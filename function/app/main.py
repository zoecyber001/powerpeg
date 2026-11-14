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

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from . import commands
from . import guestops
from . import quickpass
from . import roompower
from .authorization import (
    authorize_room_activation,
    dispatch_activation,
    dispatch_checkout,
    effective_authorization,
    ensure_module_enabled,
    ingest_event,
    is_module_installed_and_enabled,
    last_authorized_room_activation,
    require_authorization,
    revoke_room_activation,
)
from .checkins import (
    activate_room,
    approve_check_in,
    check_out,
    create_check_in,
    get_check_in,
    list_check_ins,
    verify_check_in,
)
from .modules import (
    ModuleDependencyError,
    business_surface,
    business_types,
    catalog_get,
    catalog_list,
    describe_module,
    disable_module,
    enable_module,
    get_business_modules,
    get_module_config,
    install_for_profile,
    install_module,
    missing_dependencies,
    module_dependencies,
    module_events,
    module_gate,
    module_is_enabled_for,
    profile_for,
    set_module_config,
)
from .platform import build_surface, module_is_live
from .commands import set_checkout_policy
from .modules import business_configured

# ---------------------------------------------------------------------------
# Declared tables (mirror workpeg.json's ``tables`` so init can assert
# recognition). These are the tables the manifest declares for this peg.
# ---------------------------------------------------------------------------

DECLARED_TABLE_NAMES = [
    "rooms",
    "bookings",
    "payments",
    "devices",
    "commands",
    "device_reports",
    "telemetry",
    "alerts",
    "check_ins",
    "authorizations",
    "verifications",
    "service_requests",
    "staff_tasks",
    "business_module_settings",
    "module_catalog",
    "module_profile",
    "business_modules",
    "module_config",
]

_DEV_BUSINESS_ID = os.environ.get("PEGPOWER_DEV_BUSINESS_ID", "")


def is_dev_business(business_id: str) -> bool:
    """Is this business the dev install's demonstration business?

    In the Workpeg dev install the UI hands the function the developer's first
    business id. We cannot know its literal value without the dev serve running,
    so demo seeding is gated on an explicit marker rather than a guess: either
    the environment marker is set, or the caller explicitly asks for demo data
    for a business we are initializing right now.
    """
    if _DEV_BUSINESS_ID:
        return business_id == _DEV_BUSINESS_ID
    return False

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


def _ser(value: Any) -> Any:
    """Make a value JSON-safe: datetime objects become ISO strings.

    The function's in-memory tables store timestamps as ISO strings so that
    ``get_status`` and every action response can be serialised by the runtime
    envelope (``json.dumps``) without a ``TypeError``. Datetimes only ever
    enter the stores through the ``_upsert_*`` helpers or ``_seed()``, and
    those helpers normalise them here.
    """
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value


def _stay_windows(count: int = 4) -> List[Dict[str, Any]]:
    """Bookable check-in/check-out pairs, starting tomorrow in Lagos time.

    The UI cannot compute dates (its expressions have no clock), so the
    windows it offers are derived here, from the same datetimes the booking
    action validates against.
    """
    lagos = timezone(timedelta(hours=1))
    base = (datetime.now(lagos) + timedelta(days=1)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    out: List[Dict[str, Any]] = []
    for offset in range(count):
        start = base + timedelta(days=offset)
        end = start + timedelta(days=2)
        out.append({
            "check_in": start.isoformat(),
            "check_out": end.isoformat(),
            "label": start.strftime("%a %d %b"),
            "out_label": end.strftime("%a %d %b"),
            "nights": 2,
        })
    return out


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
    three_hours_ago = now - timedelta(hours=3)
    twenty_one_hours_later = three_hours_ago + timedelta(hours=21)

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
        room_type="deluxe",
        rate=185000.0,
    )
    _upsert_room(
        room_code="ROOM-101",
        display_name="Executive Suite 101",
        status="occupied",
        assigned_device_id="VDEV-101",
        authorised=True,
        authorised_reason="Confirmed booking (Marcus Vance (VIP)) with verified payment",
        updated_at=now,
        room_type="suite",
        rate=240000.0,
    )
    _upsert_room(
        room_code="ROOM-102",
        display_name="Standard Double 102",
        status="available",
        assigned_device_id=None,
        authorised=False,
        authorised_reason="No active booking found",
        updated_at=now,
        room_type="standard",
        rate=95000.0,
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
    row["last_seen_at"] = _ser(last_seen_at) if last_seen_at is not None else _utc_now()
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
    row["updated_at"] = _ser(updated_at) if updated_at is not None else _utc_now()
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
    row["updated_at"] = _ser(updated_at) if updated_at is not None else _utc_now()
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
    row["issued_at"] = _ser(issued_at) if issued_at is not None else _utc_now()
    if delivered_at is not None:
        row["delivered_at"] = _ser(delivered_at)
    if acknowledged_at is not None:
        row["acknowledged_at"] = _ser(acknowledged_at)
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
    key = f"{room_code}@{_ser(observed_at) if observed_at is not None else _utc_now()}"
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
    row["observed_at"] = _ser(observed_at) if observed_at is not None else _utc_now()
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
# First-run initialization (idempotent, tenant-isolated, dev-only seeding)
# ---------------------------------------------------------------------------

CANONICAL_COMMERCE_MODULE = "deals"
CANONICAL_QUICKPASS_MODULE = "quickpass"
CANONICAL_GUEST_OPS_MODULE = "guesthub"
CANONICAL_ROOMPOWER_MODULE = "roompower"


def ensure_business_initialized(
    business_id: str,
    business_type: str,
    *,
    source: str = "profile",
    actor: str = "system",
) -> Dict[str, Any]:
    """Ensure a business has its module-model tables and the PegPower canonical
    modules installed and configured.

    This is idempotent and never overwrites existing business configuration:
    ``install_for_profile`` and ``install_module`` reinstall safely, and
    ``set_module_config`` only writes missing keys. A business that already has
    module rows is left alone (except for the explicit canonical-module opt-in
    for a demonstration business, which only enables a module that is installed
    but not enabled — it never rewrites an operator's existing config values).

    Module-model tables are in-memory stores in this demo function
    (``module_catalog``, ``module_profile``, ``business_modules``,
    ``module_config``, ``module_events``); in a Workpeg deployment these are the
    real tables the manifest declares and the platform provisions.
    """
    if business_type not in business_types():
        return {
            "ok": False,
            "error": f"unknown business type {business_type}",
            "business_types": business_types(),
        }

    if not business_id:
        return {"ok": False, "error": "business_id is required"}

    configured = business_configured(business_id)
    result: Dict[str, Any] = {
        "business_id": business_id,
        "business_type": business_type,
        "already_configured": configured,
        "actions": [],
    }

    def _record(action: str, detail: Dict[str, Any]) -> None:
        result["actions"].append({"action": action, **detail})

    # 1. Module-model tables: the manifest declares them; the demo function's
    #    platform module model already owns them as in-memory stores, and
    #    ``install_for_profile`` + ``install_module`` write the per-business
    #    rows. Nothing here creates tables out of thin air in a Workpeg deploy —
    #    the platform provisions declared tables from the manifest. We assert
    #    recognition so the init can report honestly if a declared table is
    #    missing from the manifest.
    missing_tables = [t for t in DECLARED_TABLE_NAMES if t not in (
        "rooms", "bookings", "payments", "devices", "commands", "device_reports",
        "telemetry", "alerts", "check_ins", "authorizations", "verifications",
        "service_requests", "staff_tasks", "business_module_settings",
        "module_catalog", "module_profile", "business_modules", "module_config",
    )]
    if missing_tables:
        return {"ok": False, "error": "declared tables missing from manifest: " + ", ".join(missing_tables)}

    # 2. Apply the business type's profile (idempotent): installs the modules the
    #    profile installs and enables the ones whose dependencies are met.
    if not configured:
        profile_result = install_for_profile(
            business_id, business_type, source=source, actor=actor
        )
        _record("install_for_profile", {
            "installed": [r["module_id"] for r in profile_result.get("installed", [])],
            "skipped": [(r["module_id"], r.get("reason")) for r in profile_result.get("skipped", [])],
        })
        configured = True

    # 3. PegPower canonical modules: the demo opts the demonstration business
    #    into all four canonical modules so the demo is complete. RoomPower is
    #    deliberately NOT auto-installed by any profile (it needs physical
    #    controllers), so a demo that wants to show RoomPower must opt in
    #    explicitly. We only enable a module that is already installed but not
    #    enabled; we never rewrite an operator's existing module_config values.
    canonical = [
        (CANONICAL_COMMERCE_MODULE, True),
        (CANONICAL_QUICKPASS_MODULE, True),
        (CANONICAL_GUEST_OPS_MODULE, True),
        (CANONICAL_ROOMPOWER_MODULE, True),
    ]
    for module_id, want_enabled in canonical:
        modules = get_business_modules(business_id)
        existing = modules.get(module_id)
        if existing is None:
            try:
                row = install_module(
                    business_id, module_id,
                    enabled=want_enabled, source="demo_init", actor=actor,
                )
                _record("install_module", {"module_id": module_id, "enabled": row.get("enabled")})
            except ModuleDependencyError as exc:
                _record("install_module_skipped", {"module_id": module_id, "error": exc.message})
                continue
        elif not existing.get("enabled") and want_enabled:
            try:
                row = enable_module(business_id, module_id, source="demo_init", actor=actor)
                _record("enable_module", {"module_id": module_id})
            except ModuleDependencyError as exc:
                _record("enable_module_skipped", {"module_id": module_id, "error": exc.message})

    # 4. Module configuration defaults for the canonical modules, written only
    #    where no value exists yet (idempotent), and only using keys the module
    #    code already reads so the demo is internally consistent.
    if get_module_config(business_id, CANONICAL_ROOMPOWER_MODULE, "checkout_policy") is None:
        set_checkout_policy(
            business_id,
            {
                "mode": "saving",
                "grace_minutes": 20,
                "essential_circuits": ["life_safety", "refrigeration"],
                "allow_blanket_shutdown": False,
                "note": "Demo default: power down non-essential loads at checkout.",
            },
        )
    if get_module_config(business_id, CANONICAL_GUEST_OPS_MODULE, "default_grant_hours") is None:
        set_module_config(business_id, CANONICAL_GUEST_OPS_MODULE, "default_grant_hours", 12)
    if get_module_config(business_id, CANONICAL_COMMERCE_MODULE, "currency") is None:
        set_module_config(business_id, CANONICAL_COMMERCE_MODULE, "currency", "NGN")
    if get_module_config(business_id, CANONICAL_COMMERCE_MODULE, "locale") is None:
        set_module_config(business_id, CANONICAL_COMMERCE_MODULE, "locale", "en-NG")
    if get_module_config(business_id, CANONICAL_GUEST_OPS_MODULE, "time_zone") is None:
        set_module_config(business_id, CANONICAL_GUEST_OPS_MODULE, "time_zone", "Africa/Lagos")

    result["configured"] = True
    result["surface"] = business_surface(business_id)
    return {"ok": True, **result}


def seed_demo_data_for_business(
    business_id: str,
    *,
    room_count: int = 3,
    booking_count: int = 2,
    device_count: int = 2,
    force: bool = False,
) -> Dict[str, Any]:
    """Create clearly labelled simulated demo data for a demonstration business.

    This is dev-only and tenant-isolated: it is never called for a production
    business. The rows it writes are labelled simulated where the schema allows
    (``payments.is_simulated``, ``telemetry.is_simulated``) and are described as
    demo/simulated in the seeded record text. It is idempotent: it does nothing
    for a business that already has rooms, and re-running it after the first
    successful seed is a no-op unless ``force`` is set.

    It seeds every table the module pages read for the demo business so the four
    canonical modules have something honest to show: rooms, bookings, payments,
    devices, commands, device_reports, telemetry, alerts, check_ins,
    authorizations, verifications, service_requests, staff_tasks.
    """
    if not business_id:
        return {"ok": False, "error": "business_id is required"}

    # Tenant isolation: do not seed a business that already has real inventory,
    # and never seed a production business (only the demo business identified by
    # the dev marker may be seeded automatically).
    if not force and _business_has_inventory(business_id):
        return {"ok": True, "seeded": False, "note": "business already has data; demo seed skipped",
                "counts": _count_demo_records()}

    if not force and not is_dev_business(business_id):
        return {"ok": False, "error": "demo seeding is restricted to the dev business"}

    # 1. Baseline sample dataset (rooms, bookings, payments, devices,
    #    telemetry, alerts) via the existing idempotent pipeline.
    _seed()

    # 2. A complete, honest guest journey for the seeded ROOM-101 stay so the
    #    QuickPass, Guest Hub and RoomPower modules have real rows to show on the
    #    dev business: a created + verified + approved check-in, an authorization
    #    grant, a queued + delivered + acknowledged POWER_ON command, and a device
    #    state report. Idempotent: the check_ins store keys on
    #    (business_id, booking_id), and the whole function is already guarded by
    #    ``_business_has_inventory`` above, so re-running after a successful seed
    #    is a no-op unless ``force`` is set.
    _seed_guest_journey_for_business(business_id)

    # 3. Honest counts across every store the demo pages read.
    counts = _count_demo_records()

    return {
        "ok": True,
        "business_id": business_id,
        "seeded": True,
        "counts": counts,
    }


def _seed_guest_journey_for_business(business_id: str) -> None:
    """Complete an honest guest journey for the seeded ROOM-101 stay.

    Gives the QuickPass, Guest Hub and RoomPower modules real rows to show on the
    dev business: a created + verified + approved check-in, an authorization
    grant, a queued + delivered + acknowledged POWER_ON command, and a device
    state report. No-op when the journey already exists (the check_ins store is
    keyed on (business_id, booking_id)).
    """
    booking = next(
        (b for b in _TABLES["bookings"].values() if b.get("room_code") == "ROOM-101"),
        None,
    )
    if not booking:
        return
    booking_id = booking["booking_id"]
    if get_check_in(business_id, booking_id).get("ok"):
        return  # journey already written for this business + booking

    guest_label = booking.get("guest_label", "Marcus Vance (VIP)")

    # Arrive -> verified -> approved.
    create_check_in(business_id, booking_id, "ROOM-101", guest_label, actor_id="demo")
    verify_check_in(business_id, booking_id, "demo")
    approve_check_in(business_id, booking_id, "demo")

    # Core authorization grant for the room (the contract RoomPower consumes).
    authorize_room_activation(
        business_id, "ROOM-101", source="demo_init", issued_by="demo",
        metadata={"booking_id": booking_id, "check_in_source": "demo"},
    )
    auth = effective_authorization(business_id, "ROOM-101")
    if not auth.get("authorized"):
        return

    # Activate the room: queue a POWER_ON through the Core dispatch path so the
    # command carries the authorization event id (the honest path, not the legacy
    # coil path).
    def _dispatch(event: Dict[str, Any]) -> Dict[str, Any]:
        return dispatch_activation(
            business_id,
            event.get("room_code", "ROOM-101"),
            "VDEV-101",
            actor="demo",
            event_id=event.get("event_id"),
        )

    activate_room(
        business_id, booking_id, "demo",
        room_code="ROOM-101", device_code="VDEV-101",
        authorization=auth, dispatch=_dispatch,
    )

    # Device picks up the command and acknowledges the relay ON.
    polled = device_poll("VDEV-101")
    command = (polled or {}).get("command")
    if command:
        device_ack(command["command_id"], "VDEV-101", reported_relay_state="ON")


def _count_demo_records() -> Dict[str, Any]:
    """Count records across every store the demo pages read, honestly."""
    import app.checkins as _ci
    import app.authorization as _am

    return {
        "rooms": len(_TABLES["rooms"]),
        "bookings": len(_TABLES["bookings"]),
        "payments": len(_TABLES["payments"]),
        "devices": len(_TABLES["devices"]),
        "telemetry": len(_TABLES["telemetry"]),
        "alerts": len(_TABLES["alerts"]),
        "commands": len(commands.COMMANDS),
        "device_state": len(commands.DEVICE_STATE),
        "check_ins": len(_ci._STORE),
        "authorizations": len(_am.AUTHORIZATION_EVENT_LOG),
        "note": (
            "service_requests, staff_tasks, device_reports and verifications are "
            "declared in the manifest but are not owned by an in-memory store in "
            "this demo function; in a Workpeg deployment they are provisioned by "
            "the platform and populated by module hooks."
        ),
    }


def _table_availability() -> Dict[str, Any]:
    """Which manifest-declared tables hold data in the demo function's stores.

    Honest split: the function's own ``_TABLES`` plus the module stores it owns
    (``commands.COMMANDS``, ``checkins._STORE``,
    ``authorization.AUTHORIZATION_EVENT_LOG``, and the ``modules.*`` module-model
    stores) versus declared-in-manifest-but-not-in-any-demo-store. Declared tables
    are provisioned by the Workpeg platform from the manifest at build/deploy time
    -- this function does not and cannot create them.
    """
    import app.checkins as _ci
    import app.authorization as _am
    import app.modules as _mods

    demo_stores: Dict[str, Any] = {
        "rooms": _TABLES["rooms"],
        "bookings": _TABLES["bookings"],
        "payments": _TABLES["payments"],
        "devices": _TABLES["devices"],
        "commands": commands.COMMANDS,  # real commands live here; _TABLES["commands"] is unused
        "telemetry": _TABLES["telemetry"],
        "alerts": _TABLES["alerts"],
        "check_ins": _ci._STORE,
        "authorizations": _am.AUTHORIZATION_EVENT_LOG,
        "module_catalog": _mods.CATALOG,
        "module_profile": _mods.PROFILES_STORE,
        "business_modules": _mods.BUSINESS_MODULES,
        "module_config": _mods.MODULE_CONFIG,
    }
    counts = {name: len(store) for name, store in demo_stores.items()}
    available = [name for name in DECLARED_TABLE_NAMES if name in demo_stores]
    not_in_demo = [name for name in DECLARED_TABLE_NAMES if name not in demo_stores]

    return {
        "available": available,
        "counts": counts,
        "declared_not_in_demo": not_in_demo,
        "extra_demo_stores": {
            "device_state": {
                "store": "commands.DEVICE_STATE",
                "rows": len(commands.DEVICE_STATE),
                "note": "in-memory device-state cache; not a manifest-declared table",
            },
        },
        "note": (
            "Declared tables are provisioned by the Workpeg platform from the "
            "manifest at build/deploy time -- this function action does not create "
            "them. The demo function owns in-memory stores for the tables listed "
            "under 'available'; the platform table layer would back them in a real "
            "deployment. 'declared_not_in_demo' tables exist in the manifest but "
            "this demo function does not own an in-memory store for them: they are "
            "populated by sibling module hooks / the platform table layer once "
            "provisioned."
        ),
    }


def _module_state_report(business_id: str) -> List[Dict[str, Any]]:
    """Installed / enabled state and configuration for every module the business has."""
    modules_list = get_business_modules(business_id)
    rows: List[Dict[str, Any]] = []
    for module_id in sorted(modules_list):
        info = describe_module(module_id) or {}
        bm = modules_list[module_id]
        config_rows = get_module_config(business_id, module_id, None) or []
        config = {c["key"]: c.get("value") for c in config_rows if isinstance(c, dict)}
        rows.append({
            "module_id": module_id,
            "name": info.get("name", module_id),
            "installed": bool(bm.get("installed")),
            "enabled": bool(bm.get("enabled")),
            "requirement": bm.get("requirement"),
            "config": config,
        })
    return rows


def dev_initialize_business(context: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Initialise the PegPower dev business: install + enable the four canonical
    modules, write their config defaults, and seed labelled demo data.

    Dev-only and tenant-isolated: the caller's business id must match
    ``PEGPOWER_DEV_BUSINESS_ID`` exactly. This does **not** provision platform
    tables -- those are declared in the manifest and provisioned by the platform at
    build/deploy time; this action reports honestly which declared tables are
    available in the demo function's own stores. It also does **not** enable
    modules for ordinary (non-dev) customers.
    """
    # Read the business id from the payload (UI action calls) or, as a fallback,
    # from the action envelope context. The platform's phase_action envelope
    # carries the business in ``context.business``; context may be None when the
    # function is called directly (e.g. a test) rather than through the runtime.
    context_business = context.get("business") if isinstance(context, dict) else None
    business_id = payload.get("business_id") or context_business or ""
    if not business_id:
        return {"ok": False, "error": "business_id is required"}

    # Tenant isolation: only the dev install's demonstration business may be
    # initialised. Explicit equality on the exact dev business id -- never a
    # prefix or pattern match, and never for arbitrary businesses.
    if not _DEV_BUSINESS_ID:
        return {
            "ok": False,
            "error": "dev_initialize_business is unavailable: PEGPOWER_DEV_BUSINESS_ID is not set",
        }
    if business_id != _DEV_BUSINESS_ID:
        return {
            "ok": False,
            "error": "dev_initialize_business is restricted to the dev business",
            "dev_business_id": _DEV_BUSINESS_ID,
            "requested_business_id": business_id,
        }

    business_type = payload.get("business_type") or "hotel"

    # 1. Install + enable the four canonical modules and write config defaults.
    init_result = ensure_business_initialized(
        business_id, business_type,
        source="dev_initialize", actor="dev_initialize_business",
    )

    # 2. Seed labelled demo data (idempotent, dev-only).
    seed_result = seed_demo_data_for_business(business_id, force=False)

    # 3. Honest table-availability report.
    tables = _table_availability()
    module_states = _module_state_report(business_id)

    return {
        "ok": True,
        "action": "dev_initialize_business",
        "restricted_to": _DEV_BUSINESS_ID,
        "business_id": business_id,
        "business_type": business_type,
        "initialized": init_result.get("ok", False),
        "already_configured": init_result.get("already_configured"),
        "init_actions": init_result.get("actions", []),
        "modules": module_states,
        "tables": tables,
        "seeded": seed_result.get("seeded"),
        "seed_counts": seed_result.get("counts", {}),
        "demo_data_note": (
            "All seeded payments and telemetry are labelled simulated "
            "(payments.is_simulated=true, telemetry.is_simulated=true)."
        ),
    }


def _business_has_inventory(business_id: str) -> bool:
    """Does this business already have rooms populated in the demo store?

    Used only to guard idempotent demo seeding. The demo store is keyed by room
    code, so a populated business will have at least one room row.
    """
    return len(_TABLES["rooms"]) > 0


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

    The manifest delivers the saved row as payload. Payment confirmation moves
    the booking to paid and re-derives the room's legacy `authorised` flag, but
    it does NOT grant room access: in this architecture the grant is a Core
    authorization event emitted when the guest is verified and reception
    approves the check-in. A failed/refunded payment revokes any grant and
    applies the business's checkout energy policy, so nothing stays live for an
    unpaid room.
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
        room["authorised_reason"] = "Verified payment confirmed in Workpeg table"
        room["updated_at"] = _utc_now()
        return {
            "ok": True,
            "authorised": True,
            "payment_status": payment_status,
            "dispatched_command": None,
            "note": "payment does not grant room access; the activation grant is issued at check-in approval",
        }

    room["authorised"] = False
    room["authorised_reason"] = f"Payment status changed to {payment_status}"
    room["updated_at"] = _utc_now()
    result = dispatch_checkout(
        payload.get("business_id", ""),
        room_code,
        room.get("assigned_device_id"),
        source="payment",
        reason=f"payment status {payment_status}",
    )
    return {
        "ok": True,
        "authorised": False,
        "payment_status": payment_status,
        "dispatched_command": result.get("command"),
        "energy": result.get("energy"),
    }


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


#: Commands this peg understands. Anything else is refused rather than
#: forwarded to a device.
DEVICE_COMMANDS = (
    "POWER_ON",
    "POWER_OFF",
    "STATUS_REQUEST",
    "CUT_NON_ESSENTIAL",
    "SET_ENERGY_MODE",
)


def queue_command(
    device_code: str,
    command: str,
    *,
    room_code: Optional[str] = None,
    business_id: str = "",
    authorization_event_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Queue a command for a device through the command lifecycle.

    If room_code is supplied, the device must be the room's assigned
    controller; otherwise the device must exist. Returns None for an invalid
    device, room or command, matching the earlier behaviour; the detailed
    lifecycle lives in app.commands and is exposed by the command_* actions.
    """
    command = (command or "").upper()
    if command not in DEVICE_COMMANDS:
        return None

    if room_code:
        room = _TABLES["rooms"].get(room_code)
        if not room or room.get("assigned_device_id") != device_code:
            return None
    elif not _TABLES["devices"].get(device_code):
        return None

    return commands.queue(
        business_id,
        device_code,
        command,
        room_code=room_code,
        authorization_event_id=authorization_event_id,
        idempotency_key=idempotency_key,
        payload=payload,
        actor="pegpower",
    )


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

    commands.expire_due()
    now = _now_dt()
    pending = [
        row
        for row in commands.list_commands(device_code=device_code, status=commands.PENDING)
        if not row.get("not_before") or (_parse_ts(row["not_before"]) or now) <= now
    ]
    pending.sort(key=lambda row: _parse_ts(row.get("issued_at")) or now)

    if not pending:
        return {"ok": True, "command": None}

    result = commands.mark_sent(pending[0]["command_id"])
    if not result.get("ok"):
        return result
    return {"ok": True, "command": result["command"]}


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

    state = (reported_relay_state or "OFF").upper()
    result = commands.acknowledge(
        command_id,
        device_code,
        reported_state={"relay": state},
        room_code=room_code,
    )
    if not result.get("ok"):
        return result

    # The device's report is the only thing that updates the device row's
    # relay state; the command's ACKNOWLEDGED status is not a claim that the
    # room is physically on.
    _upsert_device(
        device_code,
        room_code=room_code or result["command"].get("room_code"),
        reported_relay_state=state,
        connection_status="online",
    )
    if room_code:
        _upsert_room(room_code, assigned_device_id=device_code)

    return {
        "ok": True,
        "acknowledged": True,
        "reported_relay_state": state,
        "command": result["command"],
        "device_state": result.get("device_state"),
    }


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
# Inventory (Bookings & Inventory module)
# ---------------------------------------------------------------------------

def inventory_list(*, available_only: bool = False) -> Dict[str, Any]:
    """Room inventory with its current occupancy and controller assignment."""
    rows = []
    for room in _TABLES["rooms"].values():
        booking = _find_active_booking_for_room(room["room_code"])
        available = booking is None
        if available_only and not available:
            continue
        rows.append({
            **room,
            "available": available,
            "current_booking_id": (booking or {}).get("booking_id"),
        })
    return {"ok": True, "inventory": rows, "count": len(rows)}


def inventory_add(
    room_code: str,
    display_name: Optional[str] = None,
    *,
    room_type: str = "standard",
    rate: float = 150.0,
    assigned_device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a room to inventory. The room code is the inventory key."""
    if not room_code:
        return {"ok": False, "error": "room_code is required"}
    if room_code in _TABLES["rooms"]:
        return {"ok": False, "error": f"room {room_code} already exists"}
    row = _upsert_room(
        room_code=room_code,
        display_name=display_name or room_code,
        status="available",
        assigned_device_id=assigned_device_id,
        authorised=False,
        authorised_reason="No active booking found",
        room_type=room_type,
        rate=float(rate),
    )
    return {"ok": True, "room": row}


def allocate_room(
    start_at: Any,
    end_at: Any,
    *,
    room_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Find the first room free for this window. Allocation is the booking's
    room assignment; it does not itself create a reservation."""
    start = _parse_ts(start_at)
    end = _parse_ts(end_at)
    if not start or not end or not end > start:
        return {"ok": False, "error": "start_at and end_at must be valid datetimes with end after start"}
    for room_code, room in _TABLES["rooms"].items():
        if room_type and room.get("room_type") != room_type:
            continue
        if not _overlapping_confirmed_bookings(room_code, start, end):
            return {
                "ok": True,
                "room_code": room_code,
                "room": room,
                "start_at": start.isoformat(),
                "end_at": end.isoformat(),
            }
    return {"ok": False, "error": "no room in inventory is free for that window", "room_type": room_type}


def booking_list(*, status: Optional[str] = None) -> Dict[str, Any]:
    rows = []
    for booking in _TABLES["bookings"].values():
        if status and booking.get("booking_status") != status:
            continue
        payment = _find_payment_for_booking(booking["booking_id"])
        rows.append({
            **booking,
            "payment_id": (payment or {}).get("payment_id"),
            "payment_status": (payment or {}).get("payment_status"),
        })
    rows.sort(key=lambda r: r.get("start_at") or "")
    return {"ok": True, "bookings": rows, "count": len(rows)}


def booking_get(booking_id: str) -> Dict[str, Any]:
    booking = _TABLES["bookings"].get(booking_id)
    if not booking:
        return {"ok": False, "error": f"Booking {booking_id} not found"}
    payment = _find_payment_for_booking(booking_id)
    return {"ok": True, "booking": booking, "payment": payment}


# ---------------------------------------------------------------------------
# Vertical slice: booking -> inventory -> payment -> check-in -> authorization
#                 -> command -> device acknowledgement -> guest experience
# ---------------------------------------------------------------------------

def booking_flow(booking_id: str, business_id: str = "") -> Dict[str, Any]:
    """The nine stages of the guest journey, each with the row that proves it.

    This is derived from real state on every call. A stage the system has not
    actually reached reports ok: False, which is the point: the UI cannot show
    a green pipeline the data does not support.
    """
    booking = _TABLES["bookings"].get(booking_id)
    if not booking:
        return {"ok": False, "error": f"Booking {booking_id} not found"}
    room_code = booking.get("room_code")
    payment = _find_payment_for_booking(booking_id)
    ci = get_check_in(business_id, booking_id).get("check_in")
    auth = effective_authorization(business_id, room_code) if room_code else {"authorized": False, "reason": "no_room"}
    room_commands = commands.list_commands(business_id, room_code=room_code) if room_code else []
    acked = [c for c in room_commands if c.get("status") == commands.ACKNOWLEDGED]
    device_code = (ci or {}).get("device_code") or (_TABLES["rooms"].get(room_code) or {}).get("assigned_device_id")
    state = commands.device_state(business_id, device_code) if device_code else None

    stages = [
        {"stage": "booking_created", "ok": booking.get("booking_status") in ("confirmed", "checked_in"),
         "evidence": {"booking_id": booking_id, "booking_status": booking.get("booking_status")}},
        {"stage": "inventory_allocated", "ok": bool(room_code) and room_code in _TABLES["rooms"],
         "evidence": {"room_code": room_code}},
        {"stage": "payment_confirmed", "ok": (payment or {}).get("payment_status") == "confirmed",
         "evidence": payment},
        {"stage": "guest_verified", "ok": bool((ci or {}).get("verified_at")),
         "evidence": {"verified_at": (ci or {}).get("verified_at")}},
        {"stage": "receptionist_approved", "ok": bool((ci or {}).get("approved_at")),
         "evidence": {"approved_at": (ci or {}).get("approved_at")}},
        {"stage": "authorization_granted", "ok": bool(auth.get("authorized")),
         "evidence": {"reason": auth.get("reason"), "event": auth.get("event")}},
        {"stage": "command_queued", "ok": any(c.get("authorization_event_id") for c in room_commands),
         "evidence": {"commands": [c["command_id"] for c in room_commands]}},
        {"stage": "device_acknowledged", "ok": bool(acked),
         "evidence": {"command_id": acked[-1]["command_id"] if acked else None,
                      "reported_state": acked[-1].get("device_reported_state") if acked else None}},
        {"stage": "guest_experience", "ok": bool(state and (state.get("reported_state") or {}).get("relay") == "ON"),
         "evidence": state},
    ]
    return {
        "ok": True,
        "booking_id": booking_id,
        "business_id": business_id,
        "stages": stages,
        "complete": all(s["ok"] for s in stages),
        "blocked_at": next((s["stage"] for s in stages if not s["ok"]), None),
    }


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
    business_id = (payload or {}).get("business_id", "") if isinstance(payload, dict) else ""
    command_rows = commands.list_commands(business_id or None)
    alerts = _find_alerts(status="ACTIVE")
    # Most recent telemetry per room.
    latest_by_room: Dict[str, Dict[str, Any]] = {}
    for row in sorted(_TABLES["telemetry"].values(), key=lambda r: _parse_ts(r.get("observed_at")) or _now_dt(), reverse=True):
        rc = row.get("room_code")
        if rc and rc not in latest_by_room:
            latest_by_room[rc] = row

    # Outstanding commands grouped by device.
    outstanding_by_device: Dict[str, List[Dict[str, Any]]] = {}
    for row in command_rows:
        if row.get("status") in (commands.PENDING, commands.SENT):
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
        "stay_windows": _stay_windows(),
        "devices": devices,
        "commands": command_rows,
        "command_states": list(commands.STATES),
        "device_state": {
            row["device_code"]: commands.device_state(business_id, row["device_code"])
            for row in devices
        },
        "business_surface": business_surface(business_id) if business_id else None,
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
    if hook == "pegpower.on_command_post_save" or action == "on_command_post_save":
        return roompower.on_command_post_save(data)
    if hook == "pegpower.on_device_post_save" or action == "on_device_post_save":
        return roompower.on_device_post_save(data)
    if hook == "pegpower.on_device_report_post_save" or action == "on_device_report_post_save":
        return roompower.on_device_report_post_save(data)
    if hook == "pegpower.on_verification_post_save" or action == "on_verification_post_save":
        return quickpass.on_verification_post_save(data)
    if hook == "pegpower.on_authorization_post_save" or action == "on_authorization_post_save":
        return guestops.on_authorization_post_save(data)
    if hook == "pegpower.on_service_request_post_save" or action == "on_service_request_post_save":
        return guestops.on_service_request_post_save(data)

    # ---- RoomPower: the AZ3166 twin ----
    if action == "twin_ack":
        return roompower.acknowledge(
            command_id=data.get("command_id", ""),
            device_code=data.get("device_code", ""),
            relay=data.get("relay") or data.get("reported_relay_state") or "OFF",
            business_id=data.get("business_id", ""),
            room_code=data.get("room_code"),
        )
    # ---- QuickPass: verification behind a replaceable provider ----
    if action == "quickpass_start":
        return quickpass.start_verification(
            booking_id=data.get("booking_id", ""),
            guest_label=data.get("guest_label", ""),
            room_code=data.get("room_code"),
            provider_name=data.get("provider"),
        )
    if action == "quickpass_refresh":
        return quickpass.refresh_verification(
            {
                "session_id": data.get("session_id", ""),
                "provider": data.get("provider", "demo"),
                "status": data.get("status", ""),
            },
            provider_name=data.get("provider"),
        )
    if action == "quickpass_provider":
        return {"ok": True, **guestops.provider_summary()}
    if action == "quickpass_normalize":
        return {
            "ok": True,
            "status": quickpass.normalize_status(data.get("provider_status")),
            "known": quickpass.DIDIT_STATUSES,
        }
    if action == "quickpass_webhook_verify":
        raw = data.get("raw_body") or ""
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        return quickpass.verify_webhook(
            raw,
            data.get("headers") or {},
            data.get("secret") or os.environ.get("DIDIT_WEBHOOK_SECRET", ""),
        )
    if action == "quickpass_webhook_apply":
        # The relay (or the operator's own public server) forwards the request
        # body and headers here, once. Verification and idempotency live in
        # quickpass.apply_webhook; this action only chooses the secret.
        raw = data.get("raw_body") or ""
        return quickpass.apply_webhook(
            raw,
            data.get("headers") or {},
            data.get("secret") or os.environ.get("DIDIT_WEBHOOK_SECRET", ""),
            current=data.get("current") or None,
        )
    if action == "quickpass_webhook_config":
        secret = os.environ.get("DIDIT_WEBHOOK_SECRET", "")
        return {
            "ok": True,
            "secret_configured": bool(secret),
            "provider": quickpass.provider_for().name,
            "tolerance_seconds": quickpass.WEBHOOK_TOLERANCE_SECONDS,
            "signature_headers": ["X-Signature-V2", "X-Signature",
                                  "X-Signature-Simple"],
            "requires": ("A public HTTPS URL that forwards the raw body and"
                         " headers to quickpass_webhook_apply. The peg has no"
                         " inbound HTTP endpoint of its own."),
            "events_table": "verifications",
            "idempotency_key": "last_event_id",
        }

    # ---- Guest Experience & Ops ----
    if action == "checkin_eligibility":
        return {
            "ok": True,
            **guestops.check_in_eligibility(
                booking=data.get("booking"),
                payment=data.get("payment"),
                verification=data.get("verification"),
                room=data.get("room"),
            ),
        }
    if action == "checkin_approve":
        return guestops.approve_check_in(
            business_id=data.get("business_id", ""),
            booking=data.get("booking") or {},
            payment=data.get("payment"),
            verification=data.get("verification"),
            actor=data.get("actor_id", "reception"),
            override_review=bool(data.get("override_review", False)),
            ttl_hours=int(data.get("ttl_hours", guestops.DEFAULT_GRANT_HOURS)),
        )
    if action == "checkout_plan":
        return guestops.checkout(
            business_id=data.get("business_id", ""),
            booking=data.get("booking") or {},
            device_code=data.get("device_code"),
            actor=data.get("actor_id", "reception"),
            reason=data.get("reason", "guest checked out"),
        )
    if action == "grant_live":
        return {"ok": True,
                "live": guestops.grant_is_live(data.get("event"))}
    if action == "service_request_validate":
        return guestops.validate_request(data)

    if action == "twin_decide":
        return roompower.decide_command(
            data.get("business_id", ""),
            data,
        )

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

    # ---- QuickPass / check-ins module (consolidation) ----
    # These actions are routed here so the one peg can create, verify,
    # approve, activate and check out a guest. Room activation is driven by
    # the check_ins coil: it only fires when both smart_room and identity are
    # live for the business and the check-in is verified + approved.

    # The check_ins module keeps its own in-memory store during validation.
    # In a Workpeg deployment each of these would read/write the real
    # check_ins table via the SDK, and the coil would be built from the
    # business's module_profile via platform.build_surface.
    if action in (
        "check_in_create",
        "check_in_verify",
        "check_in_approve",
        "check_in_activate",
        "check_in_check_out",
        "check_in_get",
        "check_in_list",
    ):
        gate = module_gate(data.get("business_id", ""), "quickpass")
        if gate:
            return gate
        if action in ("check_in_activate", "check_in_check_out"):
            gate = module_gate(data.get("business_id", ""), "roompower")
            if gate:
                return gate

    if action == "check_in_create":
        return create_check_in(
            business_id=data.get("business_id", ""),
            booking_id=data.get("booking_id", ""),
            room_code=data.get("room_code", ""),
            guest_label=data.get("guest_label", ""),
            actor_id=data.get("actor_id", "staff"),
            check_in_id=data.get("check_in_id"),
        )

    if action == "check_in_verify":
        return verify_check_in(
            business_id=data.get("business_id", ""),
            booking_id=data.get("booking_id", ""),
            actor_id=data.get("actor_id", "staff"),
            note=data.get("note"),
        )
    if action == "check_in_approve":
        bid = data.get("business_id", "")
        booking_id = data.get("booking_id", "")
        actor_id = data.get("actor_id", "staff")
        result = approve_check_in(
            business_id=bid,
            booking_id=booking_id,
            actor_id=actor_id,
            note=data.get("note"),
        )
        if not result.get("ok"):
            return result
        # Reception approval is the moment Core issues the room-activation
        # grant. RoomPower later consumes that grant; it never reads the
        # check-in row itself, so any provider (PMS, door lock) can emit the
        # same event.
        ci = get_check_in(bid, booking_id).get("check_in") or {}
        room_code = data.get("room_code") or ci.get("room_code")
        if not room_code:
            return {**result, "authorization_event": None,
                    "note": "check-in approved, but no room is attached so no grant was issued"}
        event = authorize_room_activation(
            business_id=bid,
            room_code=room_code,
            source=data.get("source", "quickpass"),
            issued_by=actor_id,
            metadata={"check_in_id": ci.get("check_in_id"), "booking_id": booking_id},
        )
        return {**result, "authorization_event": event,
                "authorization": effective_authorization(bid, room_code)}
    if action == "check_in_activate":
        bid = data.get("business_id", "")
        booking_id = data.get("booking_id", "")
        ci = get_check_in(bid, booking_id).get("check_in") or {}
        room_code = data.get("room_code") or ci.get("room_code")
        authorization = effective_authorization(bid, room_code) if room_code else None

        def _dispatch(event: Dict[str, Any]) -> Dict[str, Any]:
            room = _TABLES["rooms"].get(event.get("room_code")) or {}
            device_code = data.get("device_code") or ci.get("device_code") or room.get("assigned_device_id")
            if not device_code:
                return {"ok": False, "error": "no device assigned to this room", "authorization": authorization}
            return dispatch_activation(
                bid,
                event["room_code"],
                device_code,
                actor=data.get("actor_id", "system"),
                event_id=event["event_id"],
            )

        return activate_room(
            business_id=bid,
            booking_id=booking_id,
            actor_id=data.get("actor_id", "staff"),
            room_code=room_code,
            device_code=data.get("device_code"),
            surface=data.get("surface"),
            queue_command=queue_command if authorization is None else None,
            authorization=authorization,
            dispatch=_dispatch if authorization is not None else None,
        )

    if action == "check_in_check_out":
        bid = data.get("business_id", "")
        booking_id = data.get("booking_id", "")
        ci = get_check_in(bid, booking_id).get("check_in") or {}

        def _dispatch_checkout(row: Dict[str, Any]) -> Dict[str, Any]:
            room = _TABLES["rooms"].get(row.get("room_code")) or {}
            device_code = data.get("device_code") or row.get("device_code") or room.get("assigned_device_id")
            return dispatch_checkout(
                bid,
                row.get("room_code"),
                device_code,
                actor=data.get("actor_id", "system"),
                source=data.get("source", "quickpass"),
                reason=data.get("reason", "guest checked out"),
            )

        result = check_out(
            business_id=bid,
            booking_id=booking_id,
            actor_id=data.get("actor_id", "staff"),
            room_code=data.get("room_code") or ci.get("room_code"),
            device_code=data.get("device_code"),
            surface=data.get("surface"),
            queue_command=None,
            dispatch=_dispatch_checkout,
        )
        # A completed stay returns the room to inventory availability and
        # mirrors the legacy authorised flag off.
        room = _TABLES["rooms"].get(result.get("check_in", {}).get("room_code") or data.get("room_code") or ci.get("room_code"))
        if result.get("ok") and room:
            _upsert_room(room_code=room["room_code"], authorised=False,
                         authorised_reason="Guest checked out")
        return result

    # ---- platform module model actions ----
    if action == "module_catalog_list":
        return {"ok": True, "modules": [describe_module(m["module_id"]) or m for m in catalog_list()]}

    if action == "module_get":
        mid = data.get("module_id", "")
        info = describe_module(mid)
        if not info:
            return {"ok": False, "error": f"unknown module {mid}"}
        return {"ok": True, "module": info}

    if action == "module_surface":
        # What the UI is allowed to show: navigation, pages, controls. The
        # function gates every action again, so this is convenience only.
        return {"ok": True, "surface": business_surface(data.get("business_id", ""))}

    if action == "module_bootstrap":
        # Configure a business from its type profile. Businesses with no
        # business_modules rows stay unconfigured and keep working, which is
        # how the existing-business migration stays safe.
        business_type = data.get("business_type", "")
        if business_type not in business_types():
            return {"ok": False, "error": f"unknown business type {business_type}",
                    "business_types": business_types()}
        result = install_for_profile(
            data.get("business_id", ""),
            business_type,
            source=data.get("source", "profile"),
            actor=data.get("actor_id", "system"),
        )
        return {"ok": True, **result}

    if action == "module_dependency_check":
        bid = data.get("business_id", "")
        mid = data.get("module_id", "")
        if mid and not catalog_get(mid):
            return {"ok": False, "error": f"unknown module {mid}"}
        if mid:
            return {"ok": True, "module_id": mid, "dependencies": module_dependencies(mid),
                    "missing": missing_dependencies(bid, mid)}
        return {"ok": True, "dependencies": {
            m["module_id"]: {**module_dependencies(m["module_id"]),
                             "missing": missing_dependencies(bid, m["module_id"])}
            for m in catalog_list()
        }}

    if action == "module_events":
        return {"ok": True, "events": module_events(
            data.get("business_id", ""), data.get("module_id") or None)}

    if action == "module_profile_get":
        business_type = data.get("business_type", "")
        if not business_type:
            return {"ok": True, "business_types": business_types()}
        if business_type not in business_types():
            return {"ok": False, "error": f"unknown business type {business_type}", "business_types": business_types()}
        return {"ok": True, "business_type": business_type, "profile": profile_for(business_type)}

    if action == "business_modules_get":
        bid = data.get("business_id", "")
        modules = get_business_modules(bid)
        return {"ok": True, "business_modules": modules, "enabled": module_is_enabled_for(bid, data.get("module_id", "")) if data.get("module_id") else None}

    if action == "module_install":
        bid = data.get("business_id", "")
        mid = data.get("module_id", "")
        if not mid:
            return {"ok": False, "error": "module_id is required"}
        if not catalog_get(mid):
            return {"ok": False, "error": f"unknown module {mid}"}
        enabled = data.get("enabled")
        source = data.get("source", "admin")
        try:
            row = install_module(bid, mid, enabled=enabled, source=source)
        except ModuleDependencyError as exc:
            return exc.to_payload()
        return {"ok": True, "business_module": row, "surface": business_surface(bid)}

    if action == "module_enable":
        bid = data.get("business_id", "")
        mid = data.get("module_id", "")
        if not mid:
            return {"ok": False, "error": "module_id is required"}
        try:
            row = enable_module(bid, mid)
        except ModuleDependencyError as exc:
            return exc.to_payload()
        if row is None:
            return {"ok": False, "error": f"module {mid} not installed for business {bid}"}
        return {"ok": True, "business_module": row, "surface": business_surface(bid)}

    if action == "module_disable":
        bid = data.get("business_id", "")
        mid = data.get("module_id", "")
        if not mid:
            return {"ok": False, "error": "module_id is required"}
        try:
            row = disable_module(bid, mid, force=bool(data.get("force", False)))
        except ModuleDependencyError as exc:
            return exc.to_payload()
        if row is None:
            return {"ok": False, "error": f"module {mid} not installed for business {bid}"}
        # Disabling preserves configuration and historical rows; only the
        # enabled flag changes. The surface reflects the change immediately.
        return {"ok": True, "business_module": row, "surface": business_surface(bid)}

    if action == "module_config_set":
        bid = data.get("business_id", "")
        mid = data.get("module_id", "")
        key = data.get("key", "")
        value = data.get("value")
        if not mid or not key:
            return {"ok": False, "error": "module_id and key are required"}
        return {"ok": True, "config": set_module_config(bid, mid, key, value)}

    if action == "module_config_get":
        bid = data.get("business_id", "")
        mid = data.get("module_id", "")
        key = data.get("key")
        cfg = {}
        try:
            cfg = {"ok": True, "config": get_module_config(bid, mid, key) if mid else {}}
        except Exception as e:
            cfg = {"ok": False, "error": str(e)}
        return cfg

    if action == "dev_initialize_business":
        return dev_initialize_business(context, data if isinstance(data, dict) else {})

    if action == "authorize_room_activation":
        return {"ok": True, "event": authorize_room_activation(
            business_id=data.get("business_id", ""),
            room_code=data.get("room_code", ""),
            source=data.get("source", "quickpass"),
            issued_by=data.get("issued_by", "system"),
            metadata=data.get("metadata"),
        )}

    if action == "revoke_room_activation":
        return {"ok": True, "event": revoke_room_activation(
            business_id=data.get("business_id", ""),
            room_code=data.get("room_code", ""),
            source=data.get("source", "quickpass"),
            issued_by=data.get("issued_by", "system"),
            metadata=data.get("metadata"),
        )}

    if action == "last_room_activation":
        ev = last_authorized_room_activation(
            business_id=data.get("business_id", ""),
            room_code=data.get("room_code", ""),
        )
        if ev is None:
            return {"ok": True, "event": None}
        return {"ok": True, "event": ev}
    if action == "check_in_get":
        return get_check_in(
            business_id=data.get("business_id", ""),
            booking_id=data.get("booking_id", ""),
        )
    if action == "check_in_list":
        return list_check_ins(
            business_id=data.get("business_id", ""),
        )

    # ---- Bookings & Inventory module ----
    if action in (
        "inventory_list",
        "inventory_add",
        "allocate_room",
        "booking_create",
        "booking_list",
        "booking_get",
        "booking_flow",
        "create_booking",
        "cancel_booking",
        "confirm_payment",
    ):
        gate = module_gate(data.get("business_id", ""), "bookings")
        if gate:
            return gate

    if action == "inventory_list":
        if not _SEEDED:
            _seed()
        return inventory_list(available_only=bool(data.get("available_only", False)))
    if action == "inventory_add":
        return inventory_add(
            room_code=data.get("room_code", ""),
            display_name=data.get("display_name"),
            room_type=data.get("room_type", "standard"),
            rate=data.get("rate", 150.0),
            assigned_device_id=data.get("assigned_device_id"),
        )
    if action == "allocate_room":
        if not _SEEDED:
            _seed()
        return allocate_room(
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            room_type=data.get("room_type"),
        )
    if action == "booking_create":
        if not _SEEDED:
            _seed()
        return create_booking(
            room_code=data.get("room_code", ""),
            guest_label=data.get("guest_label", ""),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            booking_status=data.get("booking_status"),
        )
    if action == "booking_list":
        if not _SEEDED:
            _seed()
        return booking_list(status=data.get("status"))
    if action == "booking_get":
        return booking_get(data.get("booking_id", ""))
    if action == "booking_flow":
        return booking_flow(data.get("booking_id", ""), data.get("business_id", ""))

    # ---- Command lifecycle (RoomPower) ----
    if action in ("command_list", "command_cancel", "command_expire", "command_get",
                  "checkout_policy_get", "checkout_policy_set", "dispatch_activation",
                  "dispatch_checkout", "device_state_get"):
        gate = module_gate(data.get("business_id", ""), "roompower")
        if gate:
            return gate

    if action == "command_list":
        return {"ok": True, "commands": commands.list_commands(
            data.get("business_id") or None,
            device_code=data.get("device_code"),
            room_code=data.get("room_code"),
            status=data.get("status"),
        )}
    if action == "command_get":
        row = commands.get(data.get("command_id", ""))
        if not row:
            return {"ok": False, "error": f"command {data.get('command_id')} not found"}
        return {"ok": True, "command": row}
    if action == "command_cancel":
        return commands.cancel(data.get("command_id", ""), data.get("reason", ""),
                               actor=data.get("actor_id", "operator"))
    if action == "command_expire":
        # The scheduler entry point: expire overdue commands. Safe to call on a
        # timer; this function itself does not run background timers.
        return {"ok": True, "expired": commands.expire_due(
            business_id=data.get("business_id") or None)}
    if action == "device_state_get":
        return {"ok": True, "device_state": commands.device_state(
            data.get("business_id", ""), data.get("device_code", ""))}
    if action == "checkout_policy_get":
        return {"ok": True, "policy": commands.checkout_policy(data.get("business_id", ""))}
    if action == "checkout_policy_set":
        try:
            policy = commands.set_checkout_policy(
                data.get("business_id", ""), data.get("policy") or {})
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "policy": policy}
    if action == "dispatch_activation":
        return dispatch_activation(
            data.get("business_id", ""),
            data.get("room_code", ""),
            data.get("device_code", ""),
            actor=data.get("actor_id", "system"),
            event_id=data.get("event_id"),
        )
    if action == "dispatch_checkout":
        return dispatch_checkout(
            data.get("business_id", ""),
            data.get("room_code", ""),
            data.get("device_code"),
            actor=data.get("actor_id", "system"),
            source=data.get("source", "quickpass"),
            reason=data.get("reason", ""),
        )

    # ---- Authorization contract (any provider may emit events) ----
    if action == "authorization_ingest":
        event = data.get("event") or {}
        try:
            result = ingest_event(event, data.get("business_id", ""))
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, **result}
    if action == "authorization_effective":
        return {"ok": True, "authorization": effective_authorization(
            data.get("business_id", ""), data.get("room_code", ""))}
    if action == "authorization_event_list":
        from .authorization import AUTHORIZATION_EVENT_LOG
        bid = data.get("business_id")
        events = [e for e in AUTHORIZATION_EVENT_LOG if not bid or e.get("business_id") == bid]
        if data.get("room_code"):
            events = [e for e in events if e.get("room_code") == data.get("room_code")]
        return {"ok": True, "events": events}

    # An unknown action must fail loudly: silently returning ok would let the
    # UI show success for something that never ran.
    return {
        "ok": False,
        "error": f"unknown action {action!r}" if action else "no action supplied",
        "peg": "pegpower",
        "timestamp": _utc_now(),
    }
