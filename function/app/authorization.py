"""PegPower Core authorization and event contract layer.

This is the shared layer between QuickPass, RoomPower and other modules. It
validates authorization events at the platform layer and exposes the contract
RoomPower consumes for authorized room activation.

Why this layer exists: RoomPower must NOT require QuickPass. It consumes a
Core-validated authorization contract. QuickPass is the provider implemented
today; a PMS or door-lock integration can emit the same shape through
`ingest_event` and RoomPower behaves identically.

The contract is one event:

    {event_id, business_id, room_code, authorization_type, status,
     source, issued_by, issued_at, expires_at, metadata}

`status` is "granted" or "revoked". Everything the consumer needs is here, so
no module needs to reach into another module's tables.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from . import commands
from .modules import (
    build_authorization_event,
    catalog_get,
    enable_module,
    get_business_modules,
    install_module,
    module_is_enabled_for,
    revoke_authorization_event,
    set_module_config,
    validate_authorization_event,
)

#: All events Core has accepted, in order.
AUTHORIZATION_EVENT_LOG: list[dict[str, Any]] = []

#: event_id -> event. Used to make ingestion idempotent, so a provider retrying
#: a webhook cannot activate a room twice.
_EVENT_INDEX: dict[str, dict[str, Any]] = {}

#: Default life of a granted room activation.
DEFAULT_AUTHORIZATION_TTL_HOURS = 12


def ensure_module_enabled(
    business_id: str,
    module_id: str,
    *,
    install_if_missing: bool = False,
    source: str = "admin",
) -> dict[str, Any] | None:
    """Ensure a module is installed and enabled for a business, returning the
    business_module row. This is the helper Core uses when a module needs another
    module enabled to function, without deleting any historical data.

    Raises ModuleDependencyError from the module layer when the module cannot be
    enabled yet (a hard dependency is missing).
    """
    if not catalog_get(module_id):
        return None
    modules = get_business_modules(business_id)
    row = modules.get(module_id)
    if not row:
        if not install_if_missing:
            return None
        return install_module(business_id, module_id, enabled=True, source=source)
    if row.get("enabled"):
        return row
    return enable_module(business_id, module_id, source=source)


# ---------------------------------------------------------------------------
# Event ingestion
# ---------------------------------------------------------------------------

def ingest_event(event: dict[str, Any], business_id: str) -> dict[str, Any]:
    """Accept an authorization event from any provider.

    Validates tenant and shape, then records it. A repeated `event_id` is
    accepted but not re-applied. Refuses an event whose type or source is
    missing rather than guessing.
    """
    validate_authorization_event(event, business_id)
    existing = _EVENT_INDEX.get(event["event_id"])
    if existing is not None:
        return {"event": existing, "created": False, "duplicate": True}
    _EVENT_INDEX[event["event_id"]] = event
    AUTHORIZATION_EVENT_LOG.append(event)
    return {"event": event, "created": True, "duplicate": False}


def authorize_room_activation(
    business_id: str,
    room_code: str,
    *,
    source: str = "quickpass",
    issued_by: str = "system",
    metadata: dict[str, Any] | None = None,
    event_id: str | None = None,
    ttl_hours: int | None = DEFAULT_AUTHORIZATION_TTL_HOURS,
    expires_at: str | None = None,
) -> dict[str, Any]:
    """Grant room activation. QuickPass is the current provider; the `source`
    argument is deliberately free-form so a PMS can call the same seam."""
    if expires_at is None and ttl_hours is not None:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=int(ttl_hours))
        ).isoformat()
    event = build_authorization_event(
        event_id=event_id,
        business_id=business_id,
        room_code=room_code,
        authorization_type="room_activation",
        status="granted",
        source=source,
        issued_by=issued_by,
        expires_at=expires_at,
        metadata=metadata,
    )
    return ingest_event(event, business_id)["event"]


def revoke_room_activation(
    business_id: str,
    room_code: str,
    *,
    source: str = "quickpass",
    issued_by: str = "system",
    metadata: dict[str, Any] | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Revoke room activation (checkout, cancellation, eviction)."""
    event = revoke_authorization_event(
        event_id=event_id,
        business_id=business_id,
        room_code=room_code,
        authorization_type="room_activation",
        source=source,
        issued_by=issued_by,
        metadata=metadata,
    )
    return ingest_event(event, business_id)["event"]


# ---------------------------------------------------------------------------
# Reading the contract
# ---------------------------------------------------------------------------

def last_authorized_room_activation(business_id: str, room_code: str) -> dict[str, Any] | None:
    """The most recent room_activation event for a room, or None.

    This is the shape RoomPower consumes without knowing who produced it.
    """
    found: dict[str, Any] | None = None
    for event in AUTHORIZATION_EVENT_LOG:
        if event.get("business_id") != business_id:
            continue
        if event.get("room_code") != room_code:
            continue
        if event.get("authorization_type") != "room_activation":
            continue
        if found is None or event["issued_at"] >= found["issued_at"]:
            found = event
    return found


def _is_expired(event: dict[str, Any], now: datetime | None = None) -> bool:
    expires_at = event.get("expires_at")
    if not expires_at:
        return False
    try:
        deadline = datetime.fromisoformat(expires_at)
    except ValueError:
        return True
    return (now or datetime.now(timezone.utc)) > deadline


def effective_authorization(business_id: str, room_code: str) -> dict[str, Any]:
    """Whether a room is currently authorised, and why.

    A grant is only effective while it is the latest event, its status is
    granted, and it has not expired. Revocation and expiry both end it.
    """
    event = last_authorized_room_activation(business_id, room_code)
    if event is None:
        return {"authorized": False, "reason": "no_authorization_event", "event": None}
    if event.get("status") != "granted":
        return {"authorized": False, "reason": "revoked", "event": event}
    if _is_expired(event):
        return {"authorized": False, "reason": "expired", "event": event}
    return {"authorized": True, "reason": "granted", "event": event}


def require_authorization(
    business_id: str,
    room_code: str,
    *,
    event_id: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (event, error). When `event_id` is given, that exact event must be
    the one in force: a stale event cannot be replayed to activate a room.
    """
    current = effective_authorization(business_id, room_code)
    if not current["authorized"]:
        return None, {
            "ok": False,
            "error": f"no valid room authorization for {room_code} ({current['reason']})",
            "authorization_reason": current["reason"],
            "module_disabled": False,
        }
    if event_id and current["event"]["event_id"] != event_id:
        return None, {
            "ok": False,
            "error": f"authorization event {event_id} is not in force for {room_code}",
            "authorization_reason": "stale_event",
        }
    return current["event"], None


# ---------------------------------------------------------------------------
# Dispatch: RoomPower's side of the contract
# ---------------------------------------------------------------------------

def dispatch_activation(
    business_id: str,
    room_code: str,
    device_code: str,
    *,
    actor: str = "system",
    event_id: str | None = None,
) -> dict[str, Any]:
    """Authorize-then-command. This is the only path by which RoomPower powers
    a room on, so a device can never be switched live without a Core-validated
    grant that is still in force.
    """
    event, error = require_authorization(business_id, room_code, event_id=event_id)
    if error:
        return error
    command = commands.queue_activation(
        business_id,
        device_code,
        room_code=room_code,
        authorization_event_id=event["event_id"],
        idempotency_key=f"activate:{event['event_id']}:{device_code}",
        actor=actor,
    )
    return {
        "ok": True,
        "authorization_event": event,
        "command": command,
        "dispatch": "queued",
        "note": "queued for the device; the room is not live until the device acknowledges",
    }


def dispatch_checkout(
    business_id: str,
    room_code: str,
    device_code: str | None,
    *,
    actor: str = "system",
    source: str = "quickpass",
    reason: str = "",
) -> dict[str, Any]:
    """Revoke authorization, then apply the business's energy policy.

    Never issues a blanket POWER_OFF: see commands.plan_checkout, which obeys
    the configured policy and preserves essential circuits.
    """
    event = revoke_room_activation(
        business_id,
        room_code,
        source=source,
        issued_by=actor,
        metadata={"reason": reason} if reason else None,
    )
    if not device_code:
        return {
            "ok": True,
            "authorization_event": event,
            "energy": {"action": "none", "reason": "no device assigned to this room"},
            "command": None,
        }
    energy = commands.plan_checkout(
        business_id,
        device_code,
        room_code=room_code,
        authorization_event_id=event["event_id"],
        idempotency_key=f"checkout:{event['event_id']}:{device_code}",
        actor=actor,
    )
    return {
        "ok": True,
        "authorization_event": event,
        "energy": energy,
        "command": energy.get("command"),
    }


def is_module_installed_and_enabled(business_id: str, module_id: str) -> bool:
    """Platform helper: is a module installed and enabled for a business?"""
    return module_is_enabled_for(business_id, module_id)


def save_module_setting(business_id: str, module_id: str, key: str, value: Any) -> dict[str, Any]:
    """Small pass-through so settings go through the same validated store."""
    return set_module_config(business_id, module_id, key, value)
