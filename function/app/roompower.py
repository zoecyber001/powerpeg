"""RoomPower: the AZ3166 digital twin and the guard in front of it.

The twin is a set of rows, not a hidden simulation: a `devices` row is what the
controller last reported about itself, a `commands` row is a request someone
made of it, and a `rooms` row is the room it serves. The browser writes those
rows; the platform calls the post-save hooks here; the hooks decide whether what
was written is allowed.

Two rules carry the module, and both are decisions rather than UI states:

1. **Power on requires a grant.** A `POWER_ON` command is admitted only while
   PegPower Core holds an effective `room_activation` grant for that room. A
   paid booking is not a grant; the grant is issued when reception approves a
   verified check-in. Without it the command is refused, with the reason Core
   gives (`no_authorization_event` / `revoked` / `expired`).

2. **The command's status is not the relay's state.** A command is a request;
   the `devices.reported_relay_state` is what the device claims about itself.
   The twin reconciles them and says so when they disagree, because the honest
   failure mode of this product is a room that is authorised on paper and dark
   in reality.

Nothing in this module switches mains electricity. The AZ3166 runs simulated
relay firmware; the reported state here is the software twin's report.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from . import commands
from .authorization import effective_authorization

#: Commands the twin understands. Anything else is refused rather than queued.
COMMAND_ACTIONS = (
    "POWER_ON",
    "POWER_OFF",
    "STATUS_REQUEST",
    "CUT_NON_ESSENTIAL",
    "SET_ENERGY_MODE",
)

#: The one command that needs a Core grant in force to be admitted.
REQUIRES_GRANT = ("POWER_ON",)

#: A command nobody acknowledges within this window is EXPIRED.
DEFAULT_TTL_SECONDS = 120

#: Relay states the twin accepts in a device report.
RELAY_STATES = ("ON", "OFF")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Admissibility: may this command be written at all?
# ---------------------------------------------------------------------------

def decide_command(
    business_id: str,
    row: dict[str, Any],
    *,
    authorization: Optional[dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Decide whether a proposed `commands` row may stand.

    Returns `{"ok": True, "row": <normalized row>}` or
    `{"ok": False, "error": ..., "reason": ...}`. The row is normalised rather
    than trusted: a caller cannot save a row that claims ACKNOWLEDGED, and the
    issue/expiry timestamps come from here, not from the browser.
    """
    action = str(row.get("command") or "").strip().upper()
    device_code = str(row.get("device_code") or "").strip()
    room_code = str(row.get("room_code") or "").strip()

    if not action:
        return {"ok": False, "reason": "missing_command",
                "error": "A command needs an action, e.g. POWER_ON."}
    if action not in COMMAND_ACTIONS:
        return {"ok": False, "reason": "unknown_command",
                "error": (f"'{action}' is not a command this controller "
                          f"understands. Known: {', '.join(COMMAND_ACTIONS)}.")}
    if not device_code:
        return {"ok": False, "reason": "missing_device",
                "error": "A command needs the device it is addressed to."}

    if action in REQUIRES_GRANT:
        if not room_code:
            return {"ok": False, "reason": "missing_room",
                    "error": (f"{action} needs a room_code, because a grant is "
                              "issued per room.")}
        grant = authorization
        if grant is None:
            grant = effective_authorization(business_id, room_code)
        if not grant.get("authorized"):
            reason = grant.get("reason") or "no_authorization_event"
            return {
                "ok": False,
                "reason": reason,
                "error": (f"{room_code} has no room activation grant in force "
                          f"({reason}). A paid booking is not a grant: "
                          "reception approval after identity verification is."),
            }

    issued = _parse(row.get("issued_at")) or (now or _now())
    ttl = int(row.get("ttl_seconds") or DEFAULT_TTL_SECONDS)
    grant = authorization
    if grant is None and room_code:
        grant = effective_authorization(business_id, room_code)
    event = (grant or {}).get("event") or {}

    normalized = {
        "command_id": str(row.get("command_id") or "").strip()
        or f"CMD-{issued.strftime('%H%M%S')}",
        "device_code": device_code,
        "room_code": room_code or None,
        "command": action,
        "status": commands.PENDING,
        "issued_at": _iso(issued),
        "sent_at": None,
        "expires_at": _iso(issued + timedelta(seconds=max(1, ttl))),
        "acknowledged_at": None,
        "authorization_event_id": (
            row.get("authorization_event_id")
            or (event.get("event_id") if action in REQUIRES_GRANT else None)
        ),
        "idempotency_key": row.get("idempotency_key") or None,
        "failure_reason": None,
        "device_reported_state": None,
    }
    return {"ok": True, "row": normalized}


# ---------------------------------------------------------------------------
# Reconciliation: what the device says about itself
# ---------------------------------------------------------------------------

def reconcile_device(
    business_id: str,
    device_row: dict[str, Any],
    *,
    room_code: Optional[str] = None,
    authorization: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Compare a device's reported relay state with the grant in force.

    Three outcomes matter, and none of them is a command status:

    * `live`               - relay ON and a grant is in force: the room is up.
    * `unauthorized_load`  - relay ON with no grant: the rogue-energy case.
    * `state_mismatch`     - relay OFF while a grant is in force: the guest is
                             checked in and the room is dark.

    A room with no device assigned is not an anomaly; that is a property that
    has not been wired yet, and saying so is the honest answer.
    """
    relay = str(device_row.get("reported_relay_state") or "").strip().upper()
    room = str(room_code or device_row.get("room_code") or "").strip()

    if relay not in RELAY_STATES:
        return {"ok": False, "reason": "unknown_relay_state",
                "error": f"'{relay}' is not a relay state; expected ON or OFF."}

    grant = authorization
    if grant is None and room:
        grant = effective_authorization(business_id, room)
    authorized = bool((grant or {}).get("authorized"))

    if relay == "ON" and not authorized:
        return {
            "ok": True,
            "state": "unauthorized_load",
            "room_code": room,
            "relay": relay,
            "authorized": False,
            "authorization_reason": (grant or {}).get("reason"),
            "message": (f"{device_row.get('device_code', 'This device')} "
                        f"reports the relay ON in {room or 'its room'} with no "
                        "activation grant in force."),
        }
    if relay == "OFF" and authorized:
        return {
            "ok": True,
            "state": "state_mismatch",
            "room_code": room,
            "relay": relay,
            "authorized": True,
            "message": (f"{room} has an activation grant, but "
                        f"{device_row.get('device_code', 'the device')} reports "
                        "the relay OFF."),
        }
    if relay == "ON":
        return {"ok": True, "state": "live", "room_code": room, "relay": relay,
                "authorized": True, "message": f"{room or 'The room'} is live."}
    return {"ok": True, "state": "off", "room_code": room, "relay": relay,
            "authorized": False,
            "message": f"{room or 'The room'} is off, as recorded."}


# ---------------------------------------------------------------------------
# Hooks: what the platform calls when a row is saved
# ---------------------------------------------------------------------------

def on_command_post_save(payload: dict[str, Any]) -> dict[str, Any]:
    """Hook `pegpower.on_command_post_save`.

    The saved `commands` row is a request, so this is the one place a power-on
    can be stopped. An admitted command is also queued in the lifecycle store so
    its transitions, expiry and audit trail are the Core ones rather than a
    second copy invented by the UI.
    """
    business_id = str(payload.get("business_id") or "")
    decision = decide_command(business_id, payload)
    if not decision["ok"]:
        return {
            "ok": False,
            "refused": True,
            "error": decision["error"],
            "reason": decision.get("reason"),
        }

    row = decision["row"]
    queued = commands.queue(
        business_id,
        row["device_code"],
        row["command"],
        room_code=row["room_code"],
        authorization_event_id=row["authorization_event_id"],
        idempotency_key=row["idempotency_key"],
        ttl_seconds=DEFAULT_TTL_SECONDS,
        actor="workpeg-ui",
    )
    return {
        "ok": True,
        "command": queued,
        "queued_lifecycle": queued.get("status") == commands.PENDING,
        "note": ("Accepted as a request. The relay changes when the controller "
                 "reports it, not when this row is saved."),
    }


def on_device_post_save(payload: dict[str, Any]) -> dict[str, Any]:
    """Hook `pegpower.on_device_post_save`.

    A device report is reconciled against the grant in force. A report that
    disagrees with Core is not refused - the device is the authority on its own
    relay - but it is returned as `unauthorized_load` or `state_mismatch` so the
    screen can say it out loud.
    """
    business_id = str(payload.get("business_id") or "")
    result = reconcile_device(
        business_id,
        payload,
        room_code=payload.get("room_code"),
    )
    if not result.get("ok"):
        return result
    return {
        "ok": True,
        "state": result["state"],
        "message": result["message"],
        "alert": result["state"] in ("unauthorized_load", "state_mismatch"),
    }


def acknowledge(command_id: str, device_code: str, relay: str,
                *, business_id: str = "", room_code: Optional[str] = None) -> dict[str, Any]:
    """Close a queued command with the device's own reported state.

    This is what a real controller's `device_ack` call does; the demo twin uses
    it so the command table shows ACKNOWLEDGED and the device row shows the
    relay the twin claims.
    """
    relay = str(relay or "").strip().upper()
    if relay not in RELAY_STATES:
        return {"ok": False, "error": f"'{relay}' is not a relay state; expected ON or OFF."}
    result = commands.acknowledge(
        command_id,
        device_code,
        reported_state={"relay": relay},
        room_code=room_code,
        actor="az3166-twin",
    )
    if result.get("ok") and business_id:
        result["reconciliation"] = reconcile_device(
            business_id,
            {"device_code": device_code, "room_code": room_code,
             "reported_relay_state": relay},
            room_code=room_code,
        )
    return result


def on_device_report_post_save(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a `device_reports` row: a real controller's claim, append-only.

    Reports are never edited in place, so the history of what a controller said
    survives; the newest report is the device's current reported state.
    """
    relay = str(payload.get("relay_state") or "").strip().lower()
    if relay not in ("on", "off"):
        return {
            "ok": False,
            "refused": True,
            "error": f"'{relay or 'empty'}' is not a relay state; expected on or off.",
        }
    if not payload.get("device_code"):
        return {"ok": False, "refused": True,
                "error": "A device report must name the device that sent it."}
    note = ""
    if payload.get("command_id"):
        note = "Report acknowledges " + str(payload.get("command_id")) + "."
    return {"ok": True, "relay_state": relay, "note": note}
