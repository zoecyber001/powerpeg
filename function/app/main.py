"""
PegPower Workpeg Function
==========================

Honest demo implementation of the PegPower Peg for the Workpeg hackathon.

State model
-----------
The function owns room-code-keyed in-memory tables that mirror the manifest:

    rooms      - room inventory + controller assignment + current authorisation
    bookings   - guest reservations / stay access windows
    payments   - simulated booking payments
    devices    - registered IoT controllers (MXChip AZ3166 physical kit and
                 virtual nodes)
    commands   - queued POWER_ON / POWER_OFF commands issued to a device
    telemetry  - virtual software electrical readings (V, I, kW, kWh), labelled
                 as simulated
    alerts     - cross-reconciliation anomaly alerts

What this function actually does
---------------------------------
* Booking lifecycle
  - create_booking validates the stay window and checks for overlapping
    confirmed bookings on the same room before writing the row.
  - cancel_booking marks a booking cancelled and re-evaluates the room.
* Payment post_save hook (pegpower.on_payment_post_save)
  - confirmed payment -> room.authorised = True, POWER_ON queued for the
    room's assigned device.
  - anything else -> room.authorised = False, POWER_OFF queued.
  - noop if the room has no assigned device.
* Telemetry post_save hook (pegpower.on_telemetry_post_save)
  - rogue-energy anomaly: room is UNAUTHORISED but simulated power > threshold.
  - reverse anomaly: room is AUTHORISED but the assigned device reports relay
    OFF (device_state_mismatch). This was missing from the earlier revision.
* Device command flow (honest, best-effort)
  - queue_command writes a PENDING command row.
  - device_poll returns the oldest PENDING command for a device and marks it
    DELIVERED. In a real deployment a device would poll this; here it is a
    convenience endpoint for the demo and the emulator contract.
  - device_ack marks a command ACKNOWLEDGED and records the device's reported
    relay state.
  - Command retry/timeout is modelled, not driven: each command carries
    issued_at / delivered_at / acknowledged_at, and get_status exposes
    outstanding commands so a real poll loop or scheduler could chase them.
    This function itself does not run a background timer.
* Manual override (override_power)
  - An operator can force a room authorised / unauthorised for a duration.
  - The override expiry is stored on the room row; the next evaluate_room or
    get_status re-derives authorised from the override when it has expired.
* Device identity / ownership (honest checks)
  - device_poll / device_ack / queue_command all verify that the device exists
    and, where relevant, that it is the assigned controller for the room the
    caller is acting on. Where the caller provides a room_code, the function
    confirms ownership rather than trusting a device_code alone.

What this function does NOT do (and the UI should not claim it does)
----------------------------------------------------------------------
* It does not switch live mains electricity. The AZ3166 maintains a firmware-
  level simulated relay state; all electrical telemetry is produced by the
  independent software simulator and is labelled is_simulated throughout.
* Payments are simulated rows in a Workpeg Table, not a real payment gateway.
* There is no background scheduler here. Telemetry "arrives" because the
  simulator (or a test) writes rows; this function reacts to post_save hooks
  and to explicit actions.

Demo data
---------
get_status seeds a small sample dataset the first time it is called, so the UI
can render before any external table writes happen. The dataset deliberately
mixes real and simulated so the UI can be honest:

  * ROOM-204  -> AZ3166-01 (the physical MXChip AZ3166 controller in scope)
  * ROOM-101  -> VDEV-101 (a virtual node)
  * ROOM-102  -> no device (no controller assigned)

None of the telemetry in this function is a measurement from the AZ3166.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# In-memory table store
# ---------------------------------------------------------------------------

# Each table is a dict keyed by its natural key. This is intentionally simple
# and only serves the demo; the manifest declares the real tables the Peg
# would back in a Workpeg deployment.
_TABLES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "rooms": {},
    "bookings": {},
    "payments": {},
    "devices": {},
    "commands": {},
    "telemetry": {},
    "alerts": {},
}

_SEEDED = False
_COMMAND_COUNTER = 0
_ALERT_COUNTER = 0
_BOOKING_COUNTER = 0
_PAYMENT_COUNTER = 0

UNAUTHORISED_ACTIVE_POWER_KW_THRESHOLD = 0.05
NOMINAL_VOLTAGE_V = 230.0
COMMAND_TIMEOUT_SECONDS = 30


def _seed():
    global _SEEDED
    if _SEEDED:
        return
    _SEEDED = True

    now = _now_dt()

    # Devices
    _upsert_device(
        device_code="AZ3166-01",
        room_code="ROOM-204",
        device_type="AZ3166",
        connection_status="online",
        reported_relay_state="OFF",
        last_seen_at=now,
    )
    _upsert_device(
        device_code="VDEV-101",
        room_code="ROOM-101",
        device_type="VIRTUAL",
        connection_status="online",
        reported_relay_state="ON",
        last_seen_at=now,
    )

    # Rooms
    _upsert_room(
        room_code="ROOM-204",
        display_name="Ocean View Deluxe 204",
        status="available",
        assigned_device_id="AZ3166-01",
        authorised=False,
        authorised_reason="No active booking found",
        updated_at=now,
    )
    _upsert_room(
        room_code="ROOM-101",
        display_name="Executive Suite 101",
        status="occupied",
        assigned_device_id="VDEV-101",
        authorised=True,
        authorised_reason="Confirmed booking (Marcus Vance (VIP)) with verified payment",
        updated_at=now,
    )
    _upsert_room(
        room_code="ROOM-102",
        display_name="Standard Double 102",
        status="available",
        assigned_device_id=None,
        authorised=False,
        authorised_reason="No active booking found",
        updated_at=now,
    )

    # Bookings + payments
    b101_id = _next_id("booking")
    _upsert_booking(
        booking_id=b101_id,
        room_code="ROOM-101",
        guest_label="Marcus Vance (VIP)",
        start_at=three_hours_ago,
        end_at=twenty_one_hours_later,
        booking_status="confirmed",
    )
    _upsert_payment(
        payment_id=_next_id("payment"),
        booking_id=b101_id,
        payment_status="confirmed",
        amount=220.0,
        is_simulated=True,
        updated_at=three_hours_ago - timedelta(minutes=5),
    )

    b204_id = _next_id("booking")
    _upsert_booking(
        booking_id=b204_id,
        room_code="ROOM-204",
        guest_label="Alice Johnson",
        start_at=now - timedelta(minutes=10),
        end_at=now + timedelta(hours=2),
        booking_status="confirmed",
    )
    _upsert_payment(
        payment_id=_next_id("payment"),
        booking_id=b204_id,
        payment_status="pending",
        amount=150.0,
        is_simulated=True,
        updated_at=now,
    )

    # Re-evaluate rooms from the seeded bookings/payments so the sample is
    # internally consistent.
    for room_code in ("ROOM-101", "ROOM-204", "ROOM-102"):
        evaluate_room(room_code)

    # A small amount of simulated telemetry so the energy view is not empty.
    for room_code, power in (("ROOM-101", 0.95), ("ROOM-204", 0.0), ("ROOM-102", 0.0)):
        _upsert_telemetry(
            room_code=room_code,
            voltage=round(NOMINAL_VOLTAGE_V + (0.0 if power == 0.0 else 0.0), 1),
            current=round((power * 1000.0) / NOMINAL_VOLTAGE_V, 2) if power > 0 else 0.0,
            power=power,
            energy=power * 0.0,
            is_simulated=True,
            observed_at=now,
        )


# ---------------------------------------------------------------------------
# Table row helpers
# ---------------------------------------------------------------------------

def _next_id(kind: str) -> str:
    if kind == "booking":
        global _BOOKING_COUNTER
        _BOOKING_COUNTER += 1
        return f"BKG-{_BOOKING_COUNTER:03d}"
    if kind == "payment":
        global _PAYMENT_COUNTER
        _PAYMENT_COUNTER += 1
        return f"PAY-{_PAYMENT_COUNTER:03d}"
    if kind == "command":
        global _COMMAND_COUNTER
        _COMMAND_COUNTER += 1
        return f"CMD-{_COMMAND_COUNTER:03d}"
    if kind == "alert":
        global _ALERT_COUNTER
        _ALERT_COUNTER += 1
        return f"ALT-{_ALERT_COUNTER:03d}"
    return f"{kind}-{_COMMAND_COUNTER:03d}"


def _upsert_device(
    device_code: str,
    room_code: Optional[str] = None,
    device_type: str = "AZ3166",
    connection_status: str = "offline",
    reported_relay_state: str = "OFF",
    last_seen_at: Any = None,
) -> Dict[str, Any]:
    table = _TABLES["devices"]
    row: Dict[str, Any] = table.get(device_code, {})
    row["device_code"] = device_code
    row["room_code"] = room_code
    row["device_type"] = device_type
    row["connection_status"] = connection_status
    row["reported_relay_state"] = (reported_relay_state or "OFF").upper()
    row["last_seen_at"] = last_seen_at or _utc_now()
    table[device_code] = row
    return row


def _upsert_room(
    room_code: str,
    display_name: Optional[str] = None,
    status: Optional[str] = None,
    assigned_device_id: Optional[str] = None,
    authorised: Optional[bool] = None,
    authorised_reason: Optional[str] = None,
    updated_at: Any = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Upsert a room row, preserving any fields not passed in."""
    table = _TABLES["rooms"]
    row: Dict[str, Any] = dict(table.get(room_code, {}))
    row["room_code"] = room_code
    if display_name is not None:
        row["display_name"] = display_name
    if status is not None:
        row["status"] = status
    if assigned_device_id is not None:
        row["assigned_device_id"] = assigned_device_id
    if authorised is not None:
        row["authorised"] = bool(authorised)
    if authorised_reason is not None:
        row["authorised_reason"] = authorised_reason
    row.update(extra)
    row["updated_at"] = updated_at or _utc_now()
    table[room_code] = row
    return row


def _upsert_booking(
    booking_id: str,
    room_code: str,
    guest_label: str,
    start_at: Any,
    end_at: Any,
    booking_status: str = "confirmed",
) -> Dict[str, Any]:
    table = _TABLES["bookings"]
    row: Dict[str, Any] = table.get(booking_id, {})
    row["booking_id"] = booking_id
    row["room_code"] = room_code
    row["guest_label"] = guest_label
    row["start_at"] = start_at if isinstance(start_at, str) else start_at.isoformat()
    row["end_at"] = end_at if isinstance(end_at, str) else end_at.isoformat()
    row["booking_status"] = booking_status
    table[booking_id] = row
    return row


def _upsert_payment(
    payment_id: str,
    booking_id: str,
    payment_status: str,
    amount: float = 150.0,
    is_simulated: bool = True,
    updated_at: Any = None,
) -> Dict[str, Any]:
    table = _TABLES["payments"]
    row: Dict[str, Any] = table.get(payment_id, {})
    row["payment_id"] = payment_id
    row["booking_id"] = booking_id
    row["payment_status"] = payment_status
    row["amount"] = float(amount)
    row["is_simulated"] = bool(is_simulated)
    row["updated_at"] = updated_at or _utc_now()
    table[payment_id] = row
    return row


def _upsert_command(
    command_id: str,
    device_code: str,
    command: str,
    status: str = "PENDING",
    issued_at: Any = None,
    delivered_at: Any = None,
    acknowledged_at: Any = None,
) -> Dict[str, Any]:
    table = _TABLES["commands"]
    row: Dict[str, Any] = table.get(command_id, {})
    row["command_id"] = command_id
    row["device_code"] = device_code
    row["command"] = command
    row["status"] = status
    row["issued_at"] = issued_at or _utc_now()
    if delivered_at is not None:
        row["delivered_at"] = delivered_at
    if acknowledged_at is not None:
        row["acknowledged_at"] = acknowledged_at
    table[command_id] = row
    return row


def _upsert_telemetry(
    room_code: str,
    voltage: Optional[float] = None,
    current: Optional[float] = None,
    power: Optional[float] = None,
    energy: Optional[float] = None,
    is_simulated: bool = True,
    observed_at: Any = None,
) -> Dict[str, Any]:
    table = _TABLES["telemetry"]
    key = f"{room_code}@{observed_at or _utc_now()}"
    row: Dict[str, Any] = table.get(key, {})
    row["room_code"] = room_code
    if voltage is not None:
        row["voltage"] = float(voltage)
    if current is not None:
        row["current"] = float(current)
    if power is not None:
        row["power"] = float(power)
    if energy is not None:
        row["energy"] = float(energy)
    row["is_simulated"] = bool(is_simulated)
    row["observed_at"] = observed_at or _utc_now()
    table[key] = row
    return row


def _upsert_alert(
    alert_id: str,
    room_code: str,
    alert_type: str,
    severity: str = "WARNING",
    description: str = "",
    status: str = "ACTIVE",
) -> Dict[str, Any]:
    table = _TABLES["alerts"]
    existing = _find_alerts(room_code=room_code, alert_type=alert_type, status=status)
    if existing:
        row = existing[-1]
        row["status"] = status
        return row
    row: Dict[str, Any] = {}
    row["alert_id"] = alert_id
    row["room_code"] = room_code
    row["alert_type"] = alert_type
    row["severity"] = severity
    row["description"] = description
    row["status"] = status
    table[alert_id] = row
    return row


def _find_alerts(*, room_code: Optional[str] = None, alert_type: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in _TABLES["alerts"].values():
        if room_code is not None and row.get("room_code") != room_code:
            continue
        if alert_type is not None and row.get("alert_type") != alert_type:
            continue
        if status is not None and row.get("status") != status:
            continue
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------

def evaluate_room(room_code: str) -> Dict[str, Any]:
    """Re-derive a room's authorisation from its bookings, payments and any
    live override."""
    room = _TABLES["rooms"].get(room_code)
    if not room:
        return {"room_code": room_code, "authorised": False, "reason": "Room not found"}

    now = _now_dt()

    # Live override takes precedence, but only while it has not expired.
    override_valid_until = _parse_ts(room.get("override_valid_until"))
    override_reason = room.get("override_reason")
    if override_reason is not None and override_valid_until is not None and now < override_valid_until:
        room["authorised"] = bool(room.get("override_authorised", False))
        room["authorised_reason"] = override_reason
        room["updated_at"] = _utc_now()
        return {"room_code": room_code, "authorised": room["authorised"], "reason": override_reason}

    # Clear a stale override marker once it has expired.
    if room.get("override_valid_until"):
        room.pop("override_valid_until", None)
        room.pop("override_authorised", None)
        room.pop("override_reason", None)

    # Find the active confirmed booking whose window contains "now".
    active_booking: Optional[Dict[str, Any]] = None
    reason = "No active booking found"
    for booking in _TABLES["bookings"].values():
        if booking.get("room_code") != room_code:
            continue
        if booking.get("booking_status") != "confirmed":
            continue
        b_start = _parse_ts(booking.get("start_at"))
        b_end = _parse_ts(booking.get("end_at"))
        if b_start and b_end and b_start <= now <= b_end:
            active_booking = booking
            break

    if active_booking:
        payment = _find_payment_for_booking(active_booking["booking_id"])
        if payment:
            ps = (payment.get("payment_status") or "").lower()
            if ps == "confirmed":
                reason = f"Confirmed booking ({active_booking['guest_label']}) with verified payment"
                room["authorised"] = True
                room["authorised_reason"] = reason
                room["updated_at"] = _utc_now()
                return {"room_code": room_code, "authorised": True, "reason": reason}
            if ps == "pending":
                reason = f"Booking exists ({active_booking['guest_label']}) but payment is PENDING"
            elif ps == "failed":
                reason = f"Booking exists ({active_booking['guest_label']}) but payment FAILED"
            else:
                reason = "Booking payment record present but status is not confirmed"
        else:
            reason = "Booking payment record missing"

    else:
        # No active confirmed booking -> unauthorised.
        oldest_expired = None
        future_not_started = None
        for booking in _TABLES["bookings"].values():
            if booking.get("room_code") != room_code:
                continue
            b_start = _parse_ts(booking.get("start_at"))
            b_end = _parse_ts(booking.get("end_at"))
            if b_start and b_end:
                if now > b_end and (oldest_expired is None or b_end < oldest_expired):
                    oldest_expired = b_end
                elif now < b_start and (future_not_started is None or b_start < future_not_started):
                    future_not_started = b_start
        if oldest_expired is not None:
            reason = "Booking stay window expired"
        elif future_not_started is not None:
            reason = "Booking stay window has not started yet"
        else:
            reason = "No active booking found"

    room["authorised"] = False
    room["authorised_reason"] = reason
    room["updated_at"] = _utc_now()
    return {"room_code": room_code, "authorised": False, "reason": reason}


def _find_payment_for_booking(booking_id: str) -> Optional[Dict[str, Any]]:
    for row in _TABLES["payments"].values():
        if row.get("booking_id") == booking_id:
            return row
    return None


def _find_active_booking_for_room(room_code: str) -> Optional[Dict[str, Any]]:
    now = _now_dt()
    found: Optional[Dict[str, Any]] = None
    for booking in _TABLES["bookings"].values():
        if booking.get("room_code") != room_code:
            continue
        if booking.get("booking_status") != "confirmed":
            continue
        b_start = _parse_ts(booking.get("start_at"))
        b_end = _parse_ts(booking.get("end_at"))
        if b_start and b_end and b_start <= now <= b_end:
            found = booking
            break
    return found


def _overlapping_confirmed_bookings(room_code: str, start_at: datetime, end_at: datetime, exclude_booking_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return confirmed bookings for the room that overlap the window
    [start_at, end_at], excluding one we are about to update."""
    out: List[Dict[str, Any]] = []
    for booking in _TABLES["bookings"].values():
        if booking.get("room_code") != room_code:
            continue
        if booking.get("booking_status") != "confirmed":
            continue
        if exclude_booking_id and booking.get("booking_id") == exclude_booking_id:
            continue
        b_start = _parse_ts(booking.get("start_at"))
        b_end = _parse_ts(booking.get("end_at"))
        if b_start and b_end and not (end_at < b_start or start_at > b_end):
            out.append(booking)
    return out


def create_booking(
    room_code: str,
    guest_label: str,
    start_at: Any,
    end_at: Any,
    booking_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a booking and its simulated payment row. The booking is
    rejected if it would overlap an existing confirmed booking on the same
    room."""
    start = _parse_ts(start_at)
    end = _parse_ts(end_at)
    if not start or not end:
        return {"ok": False, "error": "start_at and end_at must be valid datetimes"}
    if not end > start:
        return {"ok": False, "error": "end_at must be after start_at"}

    if not _TABLES["rooms"].get(room_code):
        return {"ok": False, "error": f"Room {room_code} not found"}

    overlaps = _overlapping_confirmed_bookings(room_code, start, end)
    if overlaps:
        labels = ", ".join(b["guest_label"] for b in overlaps)
        return {
            "ok": False,
            "error": f"Overlapping confirmed booking(s) for {room_code}: {labels}",
            "overlapping": [{"guest_label": b["guest_label"], "start_at": b["start_at"], "end_at": b["end_at"]} for b in overlaps],
        }

    booking_status = (booking_status or "confirmed").lower()
    booking_id = _next_id("booking")
    _upsert_booking(
        booking_id=booking_id,
        room_code=room_code,
        guest_label=guest_label,
        start_at=start,
        end_at=end,
        booking_status=booking_status,
    )
    payment_id = _next_id("payment")
    _upsert_payment(
        payment_id=payment_id,
        booking_id=booking_id,
        payment_status="pending",
        amount=150.0,
        is_simulated=True,
    )

    # A brand-new confirmed booking can authorise a room immediately if the
    # payment were confirmed; here payment is pending, so the room stays
    # unauthorised until the payment post_save hook fires.
    evaluate_room(room_code)
    return {
        "ok": True,
        "booking_id": booking_id,
        "payment_id": payment_id,
        "payment_status": "pending",
    }


def cancel_booking(booking_id: str) -> Dict[str, Any]:
    booking = _TABLES["bookings"].get(booking_id)
    if not booking:
        return {"ok": False, "error": f"Booking {booking_id} not found"}
    booking["booking_status"] = "cancelled"
    evaluate_room(booking["room_code"])
    return {"ok": True, "booking_id": booking_id, "booking_status": "cancelled"}


def confirm_payment(payment_id: str, payment_status: str = "confirmed", amount: Optional[float] = None) -> Dict[str, Any]:
    """Update a simulated payment and re-evaluate the room. This mirrors the
    work the post_save hook does, but is available as an explicit action for
    the UI and tests."""
    payment = _TABLES["payments"].get(payment_id)
    if not payment:
        return {"ok": False, "error": f"Payment {payment_id} not found"}
    status = (payment_status or "pending").lower()
    payment["payment_status"] = status
    if amount is not None:
        payment["amount"] = float(amount)
    payment["updated_at"] = _utc_now()

    booking = _TABLES["bookings"].get(payment["booking_id"])
    if booking:
        evaluate_room(booking["room_code"])
    return {"ok": True, "payment_id": payment_id, "payment_status": status}


def on_payment_post_save(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Workpeg hook: pegpower.on_payment_post_save.

    The manifest delivers the saved row as payload. We authorise or
    un-authorise the room the payment belongs to, and queue a POWER_ON /
    POWER_OFF command for the room's assigned device if there is one.
    """
    payment_status = (payload.get("payment_status") or "").lower()
    booking_id = payload.get("booking_id")
    if not booking_id:
        return {"ok": False, "error": "payment row missing booking_id"}

    booking = _TABLES["bookings"].get(booking_id)
    if not booking:
        return {"ok": False, "error": f"booking {booking_id} not found for this payment"}

    room_code = booking.get("room_code")
    room = _TABLES["rooms"].get(room_code)
    if not room:
        return {"ok": False, "error": f"room {room_code} not found"}

    if payment_status == "confirmed":
        room["authorised"] = True
        room["authorised_reason"] = f"Verified payment confirmed in Workpeg table"
        room["updated_at"] = _utc_now()
        cmd = None
        if room.get("assigned_device_id"):
            cmd = queue_command(room["assigned_device_id"], "POWER_ON")
        return {"ok": True, "authorised": True, "dispatched_command": cmd}

    room["authorised"] = False
    room["authorised_reason"] = f"Payment status changed to {status}"
    room["updated_at"] = _utc_now()
    cmd = None
    if room.get("assigned_device_id"):
        cmd = queue_command(room["assigned_device_id"], "POWER_OFF")
    return {"ok": True, "authorised": False, "dispatched_command": cmd}


def on_booking_post_save(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Workpeg hook: pegpower.on_booking_post_save.

    We re-evaluate the room the booking belongs to so authorisation tracks the
    latest booking state."""
    booking_id = payload.get("booking_id")
    if not booking_id:
        return {"ok": True}
    booking = _TABLES["bookings"].get(booking_id)
    if not booking:
        return {"ok": True}
    evaluate_room(booking["room_code"])
    return {"ok": True}


def on_telemetry_post_save(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Workpeg hook: pegpower.on_telemetry_post_save.

    Two anomalies are checked:

    1. Rogue energy while unauthorised (the classic demo moment).
    2. Device state mismatch: the room is authorised but the assigned device
       reports its relay OFF.
    """
    room_code = payload.get("room_code")
    if not room_code:
        return {"ok": True, "anomaly_detected": False}

    power = float(payload.get("power") or 0.0)
    room = _TABLES["rooms"].get(room_code)
    is_sim = bool(payload.get("is_simulated", True))

    alert: Optional[Dict[str, Any]] = None

    if room:
        authorised = bool(room.get("authorised", False))

        # 1. Rogue energy while unauthorised.
        if not authorised and power > UNAUTHORISED_ACTIVE_POWER_KW_THRESHOLD:
            alert = _upsert_alert(
                alert_id=_next_id("alert"),
                room_code=room_code,
                alert_type="ENERGY_WHILE_UNAUTHORISED",
                severity="CRITICAL",
                description=(
                    f"Rogue load detected: {power:.2f} kW in {room_code} "
                    f"while access is UNAUTHORISED."
                ),
                status="ACTIVE",
            )

        # 2. Reverse anomaly: authorised room, relay OFF.
        if authorised:
            device_code = room.get("assigned_device_id")
            if device_code:
                device = _TABLES["devices"].get(device_code)
                if device and (device.get("reported_relay_state") or "OFF").upper() == "OFF":
                    alert = _upsert_alert(
                        alert_id=_next_id("alert"),
                        room_code=room_code,
                        alert_type="DEVICE_STATE_MISMATCH",
                        severity="WARNING",
                        description=(
                            f"Device {device_code} reports relay OFF, but "
                            f"{room_code} is AUTHORISED."
                        ),
                        status="ACTIVE",
                    )

    return {"ok": True, "anomaly_detected": bool(alert), "alert": alert}


def queue_command(device_code: str, command: str, *, room_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Queue a POWER_ON / POWER_OFF / STATUS_REQUEST command for a device.

    If room_code is supplied, the device must be the room's assigned
    controller; otherwise the device must exist.
    """
    command = (command or "").upper()
    if command not in ("POWER_ON", "POWER_OFF", "STATUS_REQUEST"):
        return None

    if room_code:
        room = _TABLES["rooms"].get(room_code)
        if not room or room.get("assigned_device_id") != device_code:
            return None
    elif not _TABLES["devices"].get(device_code):
        return None

    cmd_id = _next_id("command")
    now = _utc_now()
    cmd = _upsert_command(command_id=cmd_id, device_code=device_code, command=command, status="PENDING", issued_at=now)
    return cmd


def device_poll(device_code: str, *, room_code: Optional[str] = None) -> Dict[str, Any]:
    """Return the oldest PENDING command for a device and mark it DELIVERED.

    This is the demo/convenience equivalent of a device polling
    GET /.../commands/next. A real deployment's device would poll the runtime;
    here we expose the same idea so the UI and the emulator can exercise it.
    """
    if room_code:
        room = _TABLES["rooms"].get(room_code)
        if not room or room.get("assigned_device_id") != device_code:
            return {"ok": False, "error": f"device {device_code} is not the controller for {room_code}"}
    elif not _TABLES["devices"].get(device_code):
        return {"ok": False, "error": f"device {device_code} not found"}

    pending = [
        (cid, row)
        for cid, row in _TABLES["commands"].items()
        if row.get("device_code") == device_code and row.get("status") == "PENDING"
    ]
    pending.sort(key=lambda t: _parse_ts(t[1].get("issued_at")) or _now_dt())

    if not pending:
        return {"ok": True, "command": None}

    cmd_id, cmd = pending[0]
    cmd["status"] = "DELIVERED"
    cmd["delivered_at"] = _utc_now()
    return {"ok": True, "command": cmd}


def device_ack(command_id: str, device_code: str, reported_relay_state: str = "OFF", *, room_code: Optional[str] = None) -> Dict[str, Any]:
    """Acknowledge a command and record the device's reported relay state.

    If room_code is supplied, the device must be the room's assigned
    controller.
    """
    if room_code:
        room = _TABLES["rooms"].get(room_code)
        if not room or room.get("assigned_device_id") != device_code:
            return {"ok": False, "error": f"device {device_code} is not the controller for {room_code}"}
    elif not _TABLES["devices"].get(device_code):
        return {"ok": False, "error": f"device {device_code} not found"}

    cmd = _TABLES["commands"].get(command_id)
    if not cmd or cmd.get("device_code") != device_code:
        return {"ok": False, "error": f"command {command_id} not found for device {device_code}"}

    state = (reported_relay_state or "OFF").upper()
    cmd["status"] = "ACKNOWLEDGED"
    cmd["acknowledged_at"] = _utc_now()

    _upsert_device(device_code, room_code=cmd.get("device_code") and room_code, reported_relay_state=state, connection_status="online")
    if room_code:
        _upsert_room(room_code, assigned_device_id=device_code)

    return {"ok": True, "acknowledged": True, "reported_relay_state": state}


def override_power(room_code: str, authorised: bool, reason: str = "", duration_minutes: int = 60) -> Dict[str, Any]:
    """Apply a temporary manual override to a room's authorisation.

    The override expires after duration_minutes and the next evaluate_room /
    get_status re-derives authorisation from bookings + payments once it has.
    """
    if not _TABLES["rooms"].get(room_code):
        return {"ok": False, "error": f"Room {room_code} not found"}

    now = _now_dt()
    valid_until = now + timedelta(minutes=int(duration_minutes))
    _upsert_room(
        room_code=room_code,
        authorised=authorised,
        authorised_reason=f"Manual override: {reason}" if reason else "Manual override",
        updated_at=now,
        override_authorised=bool(authorised),
        override_reason=f"Manual override: {reason}" if reason else "Manual override",
        override_valid_until=valid_until.isoformat(),
    )

    cmd = None
    if _TABLES["rooms"][room_code].get("assigned_device_id"):
        cmd = queue_command(
            _TABLES["rooms"][room_code]["assigned_device_id"],
            "POWER_ON" if authorised else "POWER_OFF",
            room_code=room_code,
        )
    return {
        "ok": True,
        "room_code": room_code,
        "authorised": bool(authorised),
        "override_valid_until": valid_until.isoformat(),
        "dispatched_command": cmd,
    }


# ---------------------------------------------------------------------------
# Telemetry helpers (for ingest / simulator bridge)
# ---------------------------------------------------------------------------

def ingest_telemetry(
    room_code: str,
    voltage: float,
    current: float,
    power: float,
    energy: float,
    *,
    is_simulated: bool = True,
    observed_at: Any = None,
) -> Dict[str, Any]:
    """Write a telemetry row. In a Workpeg deployment this is what the
    simulator (or a device bridge) would do; here it is also callable as an
    action so the UI or tests can push sample readings."""
    row = _upsert_telemetry(
        room_code=room_code,
        voltage=voltage,
        current=current,
        power=power,
        energy=energy,
        is_simulated=is_simulated,
        observed_at=observed_at or _utc_now(),
    )
    # The post_save hook runs the anomaly checks.
    hook_result = on_telemetry_post_save(row)
    return {"ok": True, "row": row, "anomaly_detected": hook_result.get("anomaly_detected")}


# ---------------------------------------------------------------------------
# Status / snapshot the UI actually calls
# ---------------------------------------------------------------------------

def get_status(payload: Optional[Dict[str, Any]] = None, *, seed: bool = False) -> Dict[str, Any]:
    """Return a snapshot the UI can render.

    This is the main action the UI calls. It seeds the sample dataset on first
    call so the UI has something honest to show before any external tables are
    written.
    """
    if seed or not _SEEDED:
        _seed()

    rooms = list(_TABLES["rooms"].values())
    bookings = list(_TABLES["bookings"].values())
    payments = list(_TABLES["payments"].values())
    devices = list(_TABLES["devices"].values())
    commands = list(_TABLES["commands"].values())
    alerts = _find_alerts(status="ACTIVE")
    # Most recent telemetry per room.
    latest_by_room: Dict[str, Dict[str, Any]] = {}
    for row in sorted(_TABLES["telemetry"].values(), key=lambda r: _parse_ts(r.get("observed_at")) or _now_dt(), reverse=True):
        rc = row.get("room_code")
        if rc and rc not in latest_by_room:
            latest_by_room[rc] = row

    # Outstanding commands grouped by device.
    outstanding_by_device: Dict[str, List[Dict[str, Any]]] = {}
    for row in commands:
        if row.get("status") in ("PENDING", "DELIVERED"):
            dc = row.get("device_code")
            outstanding_by_device.setdefault(dc, []).append(row)

    return {
        "ok": True,
        "peg": "pegpower",
        "sample_data": True,
        "generated_at": _utc_now(),
        "rooms": rooms,
        "bookings": bookings,
        "payments": payments,
        "devices": devices,
        "commands": commands,
        "latest_telemetry_by_room": latest_by_room,
        "active_alerts": alerts,
        "outstanding_commands_by_device": outstanding_by_device,
        "config": {
            "unauthorised_active_power_kw_threshold": UNAUTHORISED_ACTIVE_POWER_KW_THRESHOLD,
            "nominal_voltage_v": NOMINAL_VOLTAGE_V,
            "command_timeout_seconds": COMMAND_TIMEOUT_SECONDS,
        },
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main(context=None, payload=None, **kwargs) -> Dict[str, Any]:
    """Workpeg function entrypoint: app.main:main.

    The runtime calls this with either (context, payload) or a single payload
    dict. Actions and hooks are dispatched from here.
    """
    if isinstance(context, dict) and payload is None and "payload" in context:
        payload = context.get("payload", {})
        context = context.get("context", {})
    elif payload is None:
        payload = context or {}
        context = {}

    action = payload.get("action", "")
    hook = payload.get("hook", "")
    data = payload.get("data", payload)

    # Hooks
    if hook == "pegpower.on_payment_post_save" or action == "on_payment_post_save":
        return on_payment_post_save(data)
    if hook == "pegpower.on_booking_post_save" or action == "on_booking_post_save":
        return on_booking_post_save(data)
    if hook == "pegpower.on_telemetry_post_save" or action == "on_telemetry_post_save":
        return on_telemetry_post_save(data)

    # Actions
    if action == "get_status":
        return get_status(data)
    if action == "create_booking":
        return create_booking(
            room_code=data.get("room_code", ""),
            guest_label=data.get("guest_label", ""),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            booking_status=data.get("booking_status"),
        )
    if action == "cancel_booking":
        return cancel_booking(data.get("booking_id", ""))
    if action == "confirm_payment":
        return confirm_payment(
            payment_id=data.get("payment_id", ""),
            payment_status=data.get("payment_status", "confirmed"),
            amount=data.get("amount"),
        )
    if action == "override_power":
        return override_power(
            room_code=data.get("room_code", ""),
            authorised=bool(data.get("authorised", False)),
            reason=data.get("reason", ""),
            duration_minutes=int(data.get("duration_minutes", 60)),
        )
    if action == "device_poll":
        return device_poll(
            data.get("device_code", ""),
            room_code=data.get("room_code"),
        )
    if action == "device_ack":
        return device_ack(
            command_id=data.get("command_id", ""),
            device_code=data.get("device_code", ""),
            reported_relay_state=data.get("reported_relay_state", "OFF"),
            room_code=data.get("room_code"),
        )
    if action == "queue_command":
        return queue_command(
            data.get("device_code", ""),
            data.get("command", ""),
            room_code=data.get("room_code"),
        )
    if action == "ingest_telemetry":
        return ingest_telemetry(
            room_code=data.get("room_code", ""),
            voltage=float(data.get("voltage", 0)),
            current=float(data.get("current", 0)),
            power=float(data.get("power", 0)),
            energy=float(data.get("energy", 0)),
            is_simulated=bool(data.get("is_simulated", True)),
            observed_at=data.get("observed_at"),
        )

    return {"ok": True, "peg": "pegpower", "timestamp": _utc_now()}
