"""Device command lifecycle for PegPower Core.

A command is a request to a device. It is deliberately separate from the
device's reported state:

    command.status        what Core believes about the *request*
    device_state.relay    what the device last reported about *itself*

Dispatch success is not physical activation. A command reaches ACKNOWLEDGED
only when the device reports back, and even then the reported state is stored
as the device's own claim rather than overwriting the command's history.

Lifecycle:
    PENDING -> SENT -> ACKNOWLEDGED
    PENDING|SENT -> FAILED | EXPIRED | CANCELLED
    ACKNOWLEDGED, FAILED, EXPIRED and CANCELLED are terminal.

(DELIVERED was used by the earlier demo code. It is not a lifecycle state;
SENT replaces it. The old action name is kept as an alias in app.main.)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .modules import config_value, set_module_config

PENDING = "PENDING"
SENT = "SENT"
ACKNOWLEDGED = "ACKNOWLEDGED"
FAILED = "FAILED"
EXPIRED = "EXPIRED"
CANCELLED = "CANCELLED"

STATES = (PENDING, SENT, ACKNOWLEDGED, FAILED, EXPIRED, CANCELLED)
TERMINAL = frozenset({ACKNOWLEDGED, FAILED, EXPIRED, CANCELLED})

#: Permitted transitions. Anything else is refused, so a late acknowledgement
#: cannot resurrect a cancelled command.
ALLOWED = {
    PENDING: {SENT, ACKNOWLEDGED, FAILED, EXPIRED, CANCELLED},
    SENT: {ACKNOWLEDGED, FAILED, EXPIRED, CANCELLED},
    ACKNOWLEDGED: set(),
    FAILED: set(),
    EXPIRED: set(),
    CANCELLED: set(),
}

DEFAULT_TTL_SECONDS = 120

#: Device state is keyed by (business_id, device_code).
DEVICE_STATE: dict[tuple[str, str], dict[str, Any]] = {}

#: Every command the business has ever issued, keyed by command_id.
COMMANDS: dict[str, dict[str, Any]] = {}

#: (business_id, idempotency_key) -> command_id. A retried request returns the
#: original command instead of issuing a second one to the room.
IDEMPOTENCY: dict[tuple[str, str], str] = {}

#: Append-only transition log; the audit trail for command state.
AUDIT: list[dict[str, Any]] = []

_counter = {"command": 0}

# ---------------------------------------------------------------------------
# Energy policy
# ---------------------------------------------------------------------------

#: Checkout must never cut a room's power wholesale by default. "saving" keeps
#: life-safety, refrigeration and medical circuits live and drops the rest.
DEFAULT_CHECKOUT_POLICY = {
    "mode": "saving",
    "grace_minutes": 15,
    "essential_circuits": ["life_safety", "refrigeration", "medical"],
    "allow_blanket_shutdown": False,
}

POLICY_MODES = ("saving", "hold", "full_shutdown")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value).astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def checkout_policy(business_id: str) -> dict[str, Any]:
    """The business's checkout energy policy, with defaults applied."""
    policy = dict(DEFAULT_CHECKOUT_POLICY)
    stored = config_value(business_id, "roompower", "checkout_policy", {}) or {}
    if isinstance(stored, dict):
        policy.update({k: v for k, v in stored.items() if v is not None})
    if policy.get("mode") not in POLICY_MODES:
        policy["mode"] = "saving"
    try:
        policy["grace_minutes"] = max(0, int(policy.get("grace_minutes", 15)))
    except (TypeError, ValueError):
        policy["grace_minutes"] = 15
    if not isinstance(policy.get("essential_circuits"), list):
        policy["essential_circuits"] = list(DEFAULT_CHECKOUT_POLICY["essential_circuits"])
    policy["allow_blanket_shutdown"] = bool(policy.get("allow_blanket_shutdown", False))
    return policy


def set_checkout_policy(business_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    """Persist a checkout policy, validating the fields that matter."""
    current = checkout_policy(business_id)
    merged = dict(current)
    if isinstance(policy, dict):
        merged.update({k: v for k, v in policy.items() if v is not None})
    if merged.get("mode") not in POLICY_MODES:
        raise ValueError(f"checkout policy mode must be one of {', '.join(POLICY_MODES)}")
    try:
        merged["grace_minutes"] = max(0, int(merged.get("grace_minutes", 15)))
    except (TypeError, ValueError):
        raise ValueError("grace_minutes must be a whole number of minutes")
    if not isinstance(merged.get("essential_circuits"), list) or not merged["essential_circuits"]:
        raise ValueError("essential_circuits must be a non-empty list")
    merged["allow_blanket_shutdown"] = bool(merged.get("allow_blanket_shutdown", False))
    set_module_config(business_id, "roompower", "checkout_policy", merged)
    return merged


# ---------------------------------------------------------------------------
# Queueing
# ---------------------------------------------------------------------------

def _audit(command: dict[str, Any], from_status: Optional[str], to_status: str,
           actor: str, detail: dict[str, Any] | None = None) -> None:
    AUDIT.append({
        "audit_id": f"CAUD-{len(AUDIT) + 1:05d}",
        "command_id": command.get("command_id"),
        "business_id": command.get("business_id"),
        "device_code": command.get("device_code"),
        "room_code": command.get("room_code"),
        "from_status": from_status,
        "to_status": to_status,
        "actor": actor,
        "at": _iso(_now()),
        "detail": dict(detail or {}),
    })


def queue(
    business_id: str,
    device_code: str,
    command: str,
    *,
    room_code: Optional[str] = None,
    authorization_event_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    actor: str = "system",
    not_before: Optional[datetime] = None,
) -> dict[str, Any]:
    """Queue a command for a device.

    An identical `idempotency_key` returns the original command with
    `deduplicated: True` instead of issuing a second one.
    """
    if idempotency_key:
        existing_id = IDEMPOTENCY.get((business_id, idempotency_key))
        if existing_id and existing_id in COMMANDS:
            original = dict(COMMANDS[existing_id])
            original["deduplicated"] = True
            return original

    _counter["command"] += 1
    command_id = f"CMD-{_counter['command']:04d}"
    now = _now()
    row: dict[str, Any] = {
        "command_id": command_id,
        "business_id": business_id,
        "device_code": device_code,
        "room_code": room_code,
        "command": (command or "").upper(),
        "status": PENDING,
        "authorization_event_id": authorization_event_id,
        "idempotency_key": idempotency_key,
        "payload": dict(payload or {}),
        "issued_at": _iso(now),
        "not_before": _iso(not_before) if not_before else None,
        "expires_at": _iso(now + timedelta(seconds=max(1, int(ttl_seconds)))),
        "sent_at": None,
        "acknowledged_at": None,
        "failed_at": None,
        "expired_at": None,
        "cancelled_at": None,
        "failure_reason": None,
        "device_reported_state": None,
    }
    COMMANDS[command_id] = row
    if idempotency_key:
        IDEMPOTENCY[(business_id, idempotency_key)] = command_id
    _audit(row, None, PENDING, actor, {"command": row["command"]})
    return dict(row)


def get(command_id: str) -> Optional[dict[str, Any]]:
    row = COMMANDS.get(command_id)
    return dict(row) if row else None


def list_commands(business_id: Optional[str] = None, *, device_code: Optional[str] = None,
                  room_code: Optional[str] = None, status: Optional[str] = None) -> list[dict[str, Any]]:
    out = []
    for row in COMMANDS.values():
        if business_id is not None and row.get("business_id") != business_id:
            continue
        if device_code is not None and row.get("device_code") != device_code:
            continue
        if room_code is not None and row.get("room_code") != room_code:
            continue
        if status is not None and row.get("status") != status:
            continue
        out.append(dict(row))
    out.sort(key=lambda r: r.get("issued_at") or "")
    return out


def _transition(row: dict[str, Any], to_status: str, actor: str,
                detail: dict[str, Any] | None = None) -> dict[str, Any]:
    from_status = row.get("status")
    if from_status in TERMINAL:
        return {"ok": False, "error": f"command {row['command_id']} is already {from_status}",
                "command": dict(row), "terminal": True}
    if to_status not in ALLOWED.get(from_status, set()):
        return {"ok": False, "error": f"cannot move command {row['command_id']} from {from_status} to {to_status}",
                "command": dict(row)}
    row["status"] = to_status
    _audit(row, from_status, to_status, actor, detail)
    return {"ok": True, "command": dict(row)}


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------

def mark_sent(command_id: str, *, actor: str = "dispatcher") -> dict[str, Any]:
    row = COMMANDS.get(command_id)
    if not row:
        return {"ok": False, "error": f"command {command_id} not found"}
    if _is_expired(row):
        expire_due()
        return {"ok": False, "error": f"command {command_id} expired before dispatch",
                "command": dict(row)}
    result = _transition(row, SENT, actor)
    if result["ok"]:
        row["sent_at"] = _iso(_now())
        result["command"] = dict(row)
    return result


def acknowledge(
    command_id: str,
    device_code: str,
    *,
    reported_state: Optional[dict[str, Any]] = None,
    room_code: Optional[str] = None,
    actor: str = "device",
) -> dict[str, Any]:
    """Record a device acknowledgement and its reported state.

    The reported state is stored as the device's claim (`device_state`) and on
    the command (`device_reported_state`); it never rewrites command history.
    """
    row = COMMANDS.get(command_id)
    if not row:
        return {"ok": False, "error": f"command {command_id} not found"}
    if row.get("device_code") != device_code:
        return {"ok": False, "error": f"command {command_id} was not issued to device {device_code}"}
    if _is_expired(row):
        expire_due()
        return {"ok": False, "error": f"command {command_id} expired before acknowledgement",
                "command": dict(row)}

    reported = dict(reported_state or {})
    result = _transition(row, ACKNOWLEDGED, actor, {"reported_state": reported})
    if not result["ok"]:
        return result

    row["acknowledged_at"] = _iso(_now())
    row["device_reported_state"] = reported or None
    if reported:
        DEVICE_STATE[(row["business_id"], device_code)] = {
            "business_id": row["business_id"],
            "device_code": device_code,
            "room_code": room_code or row.get("room_code"),
            "reported_state": reported,
            "reported_at": row["acknowledged_at"],
            "command_id": command_id,
        }
    result["command"] = dict(row)
    result["device_state"] = device_state(row["business_id"], device_code)
    return result


def fail(command_id: str, reason: str, *, actor: str = "dispatcher") -> dict[str, Any]:
    row = COMMANDS.get(command_id)
    if not row:
        return {"ok": False, "error": f"command {command_id} not found"}
    result = _transition(row, FAILED, actor, {"reason": reason})
    if result["ok"]:
        row["failed_at"] = _iso(_now())
        row["failure_reason"] = reason
        result["command"] = dict(row)
    return result


def cancel(command_id: str, reason: str = "", *, actor: str = "operator") -> dict[str, Any]:
    row = COMMANDS.get(command_id)
    if not row:
        return {"ok": False, "error": f"command {command_id} not found"}
    result = _transition(row, CANCELLED, actor, {"reason": reason})
    if result["ok"]:
        row["cancelled_at"] = _iso(_now())
        row["failure_reason"] = reason or "cancelled"
        result["command"] = dict(row)
    return result


def _is_expired(row: dict[str, Any], now: Optional[datetime] = None) -> bool:
    if row.get("status") in TERMINAL:
        return False
    expires_at = _parse(row.get("expires_at"))
    if not expires_at:
        return False
    return (now or _now()) > expires_at


def expire_due(*, business_id: Optional[str] = None, now: Optional[datetime] = None,
               actor: str = "scheduler") -> list[dict[str, Any]]:
    """Expire every overdue command that has not reached a terminal state."""
    expired = []
    for row in COMMANDS.values():
        if business_id is not None and row.get("business_id") != business_id:
            continue
        if not _is_expired(row, now):
            continue
        result = _transition(row, EXPIRED, actor, {"expires_at": row.get("expires_at")})
        if result["ok"]:
            row["expired_at"] = _iso(now or _now())
            expired.append(dict(row))
    return expired


# ---------------------------------------------------------------------------
# Device state
# ---------------------------------------------------------------------------

def device_state(business_id: str, device_code: str) -> Optional[dict[str, Any]]:
    row = DEVICE_STATE.get((business_id, device_code))
    return dict(row) if row else None


def record_device_state(business_id: str, device_code: str, reported_state: dict[str, Any],
                        *, room_code: Optional[str] = None, source: str = "telemetry") -> dict[str, Any]:
    """Record a device report that did not come from an acknowledgement."""
    row = {
        "business_id": business_id,
        "device_code": device_code,
        "room_code": room_code,
        "reported_state": dict(reported_state or {}),
        "reported_at": _iso(_now()),
        "command_id": None,
        "source": source,
    }
    DEVICE_STATE[(business_id, device_code)] = row
    return dict(row)


# ---------------------------------------------------------------------------
# Energy-aware actions (RoomPower consumes these; they are not blanket cuts)
# ---------------------------------------------------------------------------

def queue_activation(business_id: str, device_code: str, *, room_code: Optional[str],
                     authorization_event_id: Optional[str],
                     idempotency_key: Optional[str] = None,
                     actor: str = "system") -> dict[str, Any]:
    """Room is authorised: bring the room up with its normal circuits live."""
    return queue(
        business_id,
        device_code,
        "POWER_ON",
        room_code=room_code,
        authorization_event_id=authorization_event_id,
        idempotency_key=idempotency_key,
        payload={"mode": "occupied", "circuits": {"keep": ["all"]}},
        actor=actor,
    )


def plan_checkout(
    business_id: str,
    device_code: str,
    *,
    room_code: Optional[str],
    authorization_event_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    actor: str = "system",
) -> dict[str, Any]:
    """Apply the business's checkout energy policy.

    Returns a plan rather than assuming "checkout means power off":

    hold          - leave the room powered, record the decision, no command
    saving        - cut non-essential circuits, keep essential ones live
    full_shutdown - only when the operator explicitly allowed it; otherwise
                    the plan degrades to `saving` and says so
    """
    policy = checkout_policy(business_id)
    mode = policy["mode"]
    essential = list(policy["essential_circuits"])
    grace = int(policy["grace_minutes"])
    degrade_reason = None

    if mode == "full_shutdown" and not policy["allow_blanket_shutdown"]:
        mode = "saving"
        degrade_reason = ("full_shutdown is not allowed for this business; "
                          "checkout used the saving policy instead")

    if mode == "hold":
        return {
            "ok": True,
            "action": "hold",
            "mode": mode,
            "room_code": room_code,
            "device_code": device_code,
            "reason": "checkout policy holds power; a person releases the room",
            "command": None,
        }

    not_before = _now() + timedelta(minutes=grace) if grace else None
    planned = queue(
        business_id,
        device_code,
        "CUT_NON_ESSENTIAL",
        room_code=room_code,
        authorization_event_id=authorization_event_id,
        idempotency_key=idempotency_key,
        payload={
            "mode": mode,
            "keep_circuits": essential,
            "cut_circuits": ["lighting", "hvac", "entertainment", "sockets_general"],
            "grace_minutes": grace,
        },
        actor=actor,
        not_before=not_before,
    )
    return {
        "ok": True,
        "action": "cut_non_essential",
        "mode": mode,
        "room_code": room_code,
        "device_code": device_code,
        "grace_minutes": grace,
        "keep_circuits": essential,
        "not_before": planned.get("not_before"),
        "degraded_from_full_shutdown": bool(degrade_reason),
        "reason": degrade_reason or f"checkout policy: {mode}",
        "command": planned,
    }
