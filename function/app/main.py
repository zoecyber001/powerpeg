from datetime import datetime, timezone

_STATE = {
    "rooms": {
        "ROOM-204": {
            "room_code": "ROOM-204",
            "display_name": "Ocean View Deluxe 204",
            "device_code": "AZ3166-01",
            "authorised": False,
            "active_booking": None,
            "reported_relay": "OFF",
            "latest_power": 0.0
        },
        "ROOM-101": {
            "room_code": "ROOM-101",
            "display_name": "Executive Suite 101",
            "device_code": "VDEV-101",
            "authorised": True,
            "active_booking": {"guest": "Marcus Vance", "paid": True},
            "reported_relay": "ON",
            "latest_power": 0.95
        }
    },
    "commands": [],
    "alerts": [],
    "audit_trail": []
}

def _utc_now():
    return datetime.now(timezone.utc).isoformat()

def record_audit(event_type: str, actor: str, details: dict):
    entry = {
        "id": len(_STATE["audit_trail"]) + 1,
        "event_type": event_type,
        "actor": actor,
        "details": details,
        "timestamp": _utc_now()
    }
    _STATE["audit_trail"].insert(0, entry)
    return entry

def queue_device_command(device_code: str, command: str):
    cmd_id = len(_STATE["commands"]) + 1
    cmd = {
        "id": cmd_id,
        "device_code": device_code,
        "command": command,
        "status": "PENDING",
        "issued_at": _utc_now()
    }
    _STATE["commands"].append(cmd)
    record_audit("DEVICE_COMMAND_ISSUED", "SYSTEM", {"device_code": device_code, "command": command})
    return cmd

def handle_payment_post_save(payload: dict):
    payment_status = payload.get("payment_status", "").lower()
    room_code = payload.get("room_code", "ROOM-204")
    room = _STATE["rooms"].get(room_code)

    if not room:
        return {"ok": False, "error": f"Room {room_code} not found"}

    if payment_status == "confirmed":
        room["authorised"] = True
        record_audit("ROOM_AUTHORISED", "WORKPEG_HOOK", {
            "room_code": room_code,
            "reason": "Verified payment confirmed in Workpeg table"
        })
        cmd = queue_device_command(room["device_code"], "POWER_ON")
        return {"ok": True, "authorised": True, "dispatched_command": cmd}
    else:
        room["authorised"] = False
        record_audit("ROOM_UNAUTHORISED", "WORKPEG_HOOK", {
            "room_code": room_code,
            "reason": f"Payment status changed to {payment_status}"
        })
        cmd = queue_device_command(room["device_code"], "POWER_OFF")
        return {"ok": True, "authorised": False, "dispatched_command": cmd}

def handle_telemetry_post_save(payload: dict):
    room_code = payload.get("room_code", "ROOM-204")
    power = float(payload.get("power", 0.0))
    room = _STATE["rooms"].get(room_code)

    if room:
        room["latest_power"] = power

        if not room["authorised"] and power > 0.05:
            alert = {
                "id": len(_STATE["alerts"]) + 1,
                "room_code": room_code,
                "alert_type": "ENERGY_WHILE_UNAUTHORISED",
                "severity": "CRITICAL",
                "description": f"Rogue load detected: {power:.2f} kW in {room_code} while access is UNAUTHORISED.",
                "status": "ACTIVE",
                "timestamp": _utc_now()
            }
            _STATE["alerts"].insert(0, alert)
            record_audit("ENERGY_WHILE_UNAUTHORISED", "ANOMALY_ENGINE", {
                "room_code": room_code,
                "power": power
            })
            return {"ok": True, "anomaly_detected": True, "alert": alert}

    return {"ok": True, "anomaly_detected": False}

def main(context=None, payload=None, **kwargs):
    if isinstance(context, dict) and payload is None and "payload" in context:
        payload = context.get("payload", {})
        context = context.get("context", {})
    elif payload is None:
        payload = context or {}
        context = {}

    action = payload.get("action", "")
    hook = payload.get("hook", "")

    if hook == "pegpower.on_payment_post_save" or action == "on_payment_post_save":
        return handle_payment_post_save(payload.get("data", payload))
    elif hook == "pegpower.on_telemetry_post_save" or action == "on_telemetry_post_save":
        return handle_telemetry_post_save(payload.get("data", payload))

    if action == "device_poll":
        device_code = payload.get("device_code", "AZ3166-01")
        pending = [c for c in _STATE["commands"] if c["device_code"] == device_code and c["status"] == "PENDING"]
        if pending:
            cmd = pending[0]
            cmd["status"] = "DELIVERED"
            return {"ok": True, "command": cmd}
        return {"ok": True, "command": None}

    elif action == "device_ack":
        cmd_id = payload.get("command_id")
        relay_state = payload.get("reported_relay_state", "OFF")
        device_code = payload.get("device_code", "AZ3166-01")

        for cmd in _STATE["commands"]:
            if cmd["id"] == cmd_id:
                cmd["status"] = "ACKNOWLEDGED"
                cmd["acknowledged_at"] = _utc_now()
                break

        for r in _STATE["rooms"].values():
            if r["device_code"] == device_code:
                r["reported_relay"] = relay_state

        record_audit("DEVICE_COMMAND_ACKNOWLEDGED", "DEVICE", {
            "command_id": cmd_id,
            "device_code": device_code,
            "reported_relay": relay_state
        })
        return {"ok": True, "acknowledged": True}

    elif action == "get_status":
        return {
            "ok": True,
            "peg": "pegpower",
            "rooms": _STATE["rooms"],
            "active_alerts": [a for a in _STATE["alerts"] if a["status"] == "ACTIVE"],
            "recent_audit": _STATE["audit_trail"][:15]
        }

    return {
        "ok": True,
        "peg": "pegpower",
        "timestamp": _utc_now()
    }
