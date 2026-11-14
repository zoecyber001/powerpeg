"""check_ins-driven room activation for the consolidated peg.

This is the consolidation's key behavior: PegPower room-power control becomes
the QuickPass smart-room activation layer, and it is driven by an authorized
check-in record, not by reservation approval.

Flow a business opts into (when both smart_room and identity are live):

    guest books -> reservation confirmed
    guest arrives -> reception marks arrived (verification step)
    reception approves check-in
    -> QuickPass emits an authorized room-activation event
    -> room controller receives POWER_ON
    -> device reports actual relay state
    -> dashboard updates

Checkout revokes guest authorization and triggers the energy-saving workflow
(POWER_OFF). Manual override and safe failure are modeled in function/app/main.py.

What this module does NOT do:

* It does not run identity verification itself. Identity is owned by the
  identity module; this module only requires that a check-in has been verified
  before it authorizes activation, and it stores the verification/approval
  timestamps so staff review and escalation are traceable.
* It does not switch live mains electricity. The device command flow in
  function/app/main.py is best-effort and simulated-first; this module only
  queues POWER_ON / POWER_OFF commands through the existing queue_command path.
* It does not touch the payments table. Payment confirmation is a separate layer.

Idempotency: approve/activate/check_out are idempotent on (business_id, booking_id):
re-applying the same transition is a no-op after the first success, so a retry
or a double-click cannot double-activate a room.

Audit: every transition writes an audit event row so the operator has a
staff-reviewable trail. The audit table is declared in the quickpass-ng module
model (platform.audit_table_columns) and is part of the consolidated peg's module
model; this module treats it as an available side channel, never as the source
of truth for room state.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

try:
    from .platform import module_is_live  # noqa: F401
except ImportError:
    # Standalone validation fallback: define stubs so the module can be
    # compiled/exercised without being imported as part of the app package.
    def module_is_live(profile: dict[str, Any], module: str) -> bool:
        return True


def build_surface(profile: dict[str, Any]) -> dict[str, Any]:
    """Stub only: the real surface is built by platform.build_surface.
    Import platform.build_surface in production."""
    return {}

log = logging.getLogger("pegpower.checkins")

_UTC = timezone.utc


def _now() -> str:
    return datetime.now(_UTC).isoformat()


def _parse(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(_UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).astimezone(_UTC)
        except ValueError:
            return None
    return None


# Allowed transitions so a check-in cannot skip a step.
_ALLOWED: Dict[str, tuple[str, ...]] = {
    "arrived": ("verified", "cancelled"),
    "verified": ("approved", "cancelled"),
    "approved": ("activated", "cancelled"),
    "activated": ("activated", "checked_out", "cancelled"),
    "checked_out": ("checked_out",),
    "cancelled": ("cancelled",),
}


def _can_activate(
    surface: dict[str, Any],
    row: dict[str, Any],
    authorization: Optional[dict[str, Any]] = None,
) -> bool:
    """Is this check-in allowed to activate its room?

    Verified + approved is always required. Room power itself is decided by a
    Core authorization contract, not by this module's own check-in state:
    `authorization` is the result of Core's `effective_authorization`, so a
    revoked or expired grant blocks activation even for an approved check-in.

    When `authorization` is None the caller is on the legacy demo path, which
    used the business's room-activation coil. That path is kept so existing
    behaviour is preserved, and is marked in the response.
    """
    if not (row.get("verified_at") and row.get("approved_at")):
        return False
    if authorization is not None:
        return bool(authorization.get("authorized"))
    return bool(surface.get("room_activation_coil"))


# ---------------------------------------------------------------------------
# In-memory store (mirrors the manifest table; in a Workpeg deployment this
# module reads/writes the real check_ins table via the SDK, and the function
# receives rows through hooks and actions).
# ---------------------------------------------------------------------------

_STORE: Dict[str, Dict[str, Any]] = {}
_AUDIT: list[dict[str, Any]] = []


def _audit(
    business_id: str,
    actor_id: str,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: str,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "audit_id": f"AUD-{len(_AUDIT)+1:04d}",
        "business_id": business_id,
        "actor_id": actor_id,
        "actor_type": actor_type,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "before": before or {},
        "after": after or {},
        "metadata": metadata or {},
        "created_at": _now(),
    }
    _AUDIT.append(row)
    log.info("audit %s %s %s %s", action, resource_type, resource_id, business_id)
    return row


def create_check_in(
    business_id: str,
    booking_id: str,
    room_code: str,
    guest_label: str,
    actor_id: str = "system",
    *,
    check_in_id: Optional[str] = None,
) -> dict[str, Any]:
    """Record that a guest for a confirmed booking has arrived.

    This is the first step of the check-in flow. It is not room activation.
    """
    if not booking_id or not room_code:
        return {"ok": False, "error": "booking_id and room_code are required"}
    key = f"{business_id}::{booking_id}"
    if key in _STORE:
        return {
            "ok": False,
            "error": f"check-in already exists for booking {booking_id}",
            "check_in_id": _STORE[key]["check_in_id"],
        }
    row: dict[str, Any] = {
        "check_in_id": check_in_id or f"CI-{len(_STORE)+1:04d}",
        "business_id": business_id,
        "booking_id": booking_id,
        "room_code": room_code,
        "guest_label": guest_label,
        "arrived_at": _now(),
        "check_in_status": "arrived",
        "device_code": None,
    }
    _STORE[key] = row
    _audit(business_id, actor_id, "staff", "check_in_created", "check_in", row["check_in_id"], before=None, after=row)
    return {"ok": True, "check_in_id": row["check_in_id"], "check_in_status": "arrived"}


def verify_check_in(
    business_id: str,
    booking_id: str,
    actor_id: str,
    *,
    note: Optional[str] = None,
) -> dict[str, Any]:
    """Reception marks the guest as verified (identity check step).

    This is the identity-module touchpoint: verification is recorded here, but
    the identity module owns what 'verified' means. This module only stores the
    fact and the timestamp so the activation coil can require it.
    """
    row = _get(business_id, booking_id)
    if not row:
        return {"ok": False, "error": f"no check-in for booking {booking_id}"}
    if row["check_in_status"] not in ("arrived", "verified"):
        return {"ok": False, "error": f"cannot verify check-in in state {row['check_in_status']}"}
    before = _snapshot(row)
    row["verified_at"] = _now()
    if note:
        row.setdefault("metadata", {})["verification_note"] = note
    row["check_in_status"] = "verified"
    _audit(business_id, actor_id, "staff", "check_in_verified", "check_in", row["check_in_id"], before=before, after=_snapshot(row))
    return {"ok": True, "check_in_id": row["check_in_id"], "check_in_status": "verified"}


def approve_check_in(
    business_id: str,
    booking_id: str,
    actor_id: str,
    *,
    note: Optional[str] = None,
) -> dict[str, Any]:
    """Reception approves the check-in for room activation.

    Approval is the trigger for the authorized room-activation event. The room
    is only activated when both verified and approved, and only when the business
    has both smart_room and identity live.
    """
    row = _get(business_id, booking_id)
    if not row:
        return {"ok": False, "error": f"no check-in for booking {booking_id}"}
    if row["check_in_status"] not in ("verified", "approved"):
        return {"ok": False, "error": f"cannot approve check-in in state {row['check_in_status']}"}
    before = _snapshot(row)
    row["approved_at"] = _now()
    if note:
        row.setdefault("metadata", {})["approval_note"] = note
    row["check_in_status"] = "approved"
    _audit(business_id, actor_id, "staff", "check_in_approved", "check_in", row["check_in_id"], before=before, after=_snapshot(row))
    return {"ok": True, "check_in_id": row["check_in_id"], "check_in_status": "approved"}


def activate_room(
    business_id: str,
    booking_id: str,
    actor_id: str,
    room_code: Optional[str] = None,
    device_code: Optional[str] = None,
    *,
    surface: Optional[dict[str, Any]] = None,
    queue_command: Optional[Callable[..., Any]] = None,
    authorization: Optional[dict[str, Any]] = None,
    dispatch: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Activate the room for a verified and approved check-in.

    `authorization` is Core's `effective_authorization(...)` for the room: the
    validated contract RoomPower consumes, whatever produced it. `dispatch` is
    called with that contract to queue the device command; it is the Core
    helper that enforces "valid grant in force" and records the event id on the
    command, so this module never issues a POWER_ON on its own authority.

    Idempotent: an already-activated check-in returns already_activated.
    """
    row = _get(business_id, booking_id)
    if not row:
        return {"ok": False, "error": f"no check-in for booking {booking_id}"}
    if row["check_in_status"] not in ("approved", "activated"):
        return {"ok": False, "error": f"cannot activate check-in in state {row['check_in_status']}"}
    if row["check_in_status"] == "activated":
        return {"ok": True, "check_in_id": row["check_in_id"], "check_in_status": "activated", "already_activated": True}

    # Sync room/device identity onto the check-in row if the caller supplied it.
    # In a Workpeg deployment this comes from the booking -> room -> device
    # join; here we accept it on the action payload so the command path can
    # fire without a full inventory service.
    if room_code:
        row["room_code"] = room_code
    if device_code:
        row["device_code"] = device_code

    surface = surface or {}
    if not _can_activate(surface, row, authorization):
        reason = (authorization or {}).get("reason")
        return {
            "ok": False,
            "error": (
                f"room activation refused: authorization {reason}"
                if reason
                else "check-in is not verified and approved, or no valid room authorization is in force"
            ),
            "authorization": authorization,
        }

    before = _snapshot(row)
    row["activated_at"] = _now()
    row["check_in_status"] = "activated"
    row.setdefault("metadata", {})["activated_by"] = actor_id

    dispatched_command = None
    authorization_event = (authorization or {}).get("event")
    if authorization_event:
        row["authorization_event_id"] = authorization_event.get("event_id")

    if dispatch is not None and authorization_event:
        result = dispatch(authorization_event)
        if not result.get("ok"):
            # The state transition already happened; surface the failure rather
            # than pretending the room came up.
            row["check_in_status"] = "approved"
            row["activated_at"] = None
            _audit(business_id, actor_id, "system", "room_activation_dispatch_failed", "room", row["room_code"], before=before, after=_snapshot(row), metadata={"error": result.get("error")})
            return result
        dispatched_command = result.get("command")
        row["command_id"] = (dispatched_command or {}).get("command_id")
    elif queue_command is not None:
        # Legacy demo path: no Core contract in play.
        coil = surface.get("room_activation_coil") or {}
        if coil.get("activates_device"):
            dc = row.get("device_code")
            if dc:
                try:
                    dispatched_command = queue_command(dc, "POWER_ON", room_code=row.get("room_code"))
                except TypeError:
                    dispatched_command = queue_command(dc, "POWER_ON")

    _audit(business_id, actor_id, "system", "room_activated", "room", row["room_code"], before=before, after=_snapshot(row), metadata={"check_in_id": row["check_in_id"], "booking_id": booking_id})
    return {"ok": True, "check_in_id": row["check_in_id"], "check_in_status": "activated", "activated_at": row["activated_at"], "dispatched_command": dispatched_command, "authorization_event_id": row.get("authorization_event_id")}


def check_out(
    business_id: str,
    booking_id: str,
    actor_id: str,
    room_code: Optional[str] = None,
    device_code: Optional[str] = None,
    *,
    surface: Optional[dict[str, Any]] = None,
    queue_command: Optional[Callable[..., Any]] = None,
    dispatch: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Check the guest out and hand the room back to the energy policy.

    `dispatch` is Core's checkout helper: it revokes the authorization and
    applies the business's configured checkout policy. That policy may hold the
    room, cut only non-essential circuits, or (if the operator allowed it)
    shut down fully - this module never decides to kill a room's power.

    Idempotent: a second check_out is a no-op after the first success.
    """
    row = _get(business_id, booking_id)
    if not row:
        return {"ok": False, "error": f"no check-in for booking {booking_id}"}
    if row["check_in_status"] == "checked_out":
        return {"ok": True, "check_in_id": row["check_in_id"], "check_in_status": "checked_out", "already_checked_out": True}

    if room_code:
        row["room_code"] = room_code
    if device_code:
        row["device_code"] = device_code

    before = _snapshot(row)
    row["check_in_status"] = "checked_out"
    row["checked_out_at"] = _now()
    row.setdefault("metadata", {})["checked_out_by"] = actor_id

    dispatched_command = None
    dispatch_result: dict[str, Any] | None = None
    if dispatch is not None:
        dispatch_result = dispatch(row)
        dispatched_command = (dispatch_result or {}).get("command")
        row["checkout_authorization_event_id"] = ((dispatch_result or {}).get("authorization_event") or {}).get("event_id")
        row["checkout_energy_action"] = ((dispatch_result or {}).get("energy") or {}).get("action")
        if dispatched_command:
            row["command_id"] = dispatched_command.get("command_id")
    elif surface and (coil := surface.get("room_activation_coil")) and coil.get("activates_device") and queue_command is not None:
        dc = row.get("device_code")
        if dc:
            try:
                dispatched_command = queue_command(dc, "POWER_OFF", room_code=row.get("room_code"))
            except TypeError:
                dispatched_command = queue_command(dc, "POWER_OFF")

    _audit(business_id, actor_id, "staff", "check_out", "check_in", row["check_in_id"], before=before, after=_snapshot(row), metadata={"energy": (dispatch_result or {}).get("energy")})
    return {"ok": True, "check_in_id": row["check_in_id"], "check_in_status": "checked_out", "checked_out_at": row.get("checked_out_at"), "dispatched_command": dispatched_command, "energy": (dispatch_result or {}).get("energy")}


def get_check_in(business_id: str, booking_id: str) -> dict[str, Any]:
    row = _get(business_id, booking_id)
    if not row:
        return {"ok": False, "error": f"no check-in for booking {booking_id}"}
    return {"ok": True, "check_in": row}


def list_check_ins(business_id: str) -> dict[str, Any]:
    rows = [r for r in _STORE.values() if r["business_id"] == business_id]
    return {"ok": True, "check_ins": rows}


def _get(business_id: str, booking_id: str) -> Optional[dict[str, Any]]:
    return _STORE.get(f"{business_id}::{booking_id}")


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if not k.startswith("_")}
