"""In-process checks for the PegPower platform layer.

These are NOT Workpeg runtime tests. They import the function package directly
from ``function/`` and call ``app.main.main(...)`` in this Python interpreter.
A separate offline Docker build (see docs/001 §14) covers compilation and the
manifest; only running the image in a real Workpeg runtime would exercise the
platform itself.

Run:  .venv/bin/python tests/test_platform.py   (or: .venv/bin/python -m pytest)
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "function"))

import app  # noqa: E402
from app import authorization, checkins, commands, modules  # noqa: E402
from app.main import main  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: object, detail: object = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  ok   {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL {name} :: {detail}")


def call(action: str, **data):
    # The tests act as the owner: every mutating action names its caller's
    # role in the payload, and the access-control matrix is exercised
    # separately in test_access_control.
    data.setdefault("actor_role", "owner")
    return main(None, {"action": action, "data": data})


def reset() -> None:
    modules.CATALOG.clear()
    modules.PROFILES_STORE.clear()
    modules.BUSINESS_MODULES.clear()
    modules.MODULE_CONFIG.clear()
    modules.MODULE_EVENTS.clear()
    commands.COMMANDS.clear()
    commands.DEVICE_STATE.clear()
    commands.IDEMPOTENCY.clear()
    commands.AUDIT.clear()
    commands._counter["command"] = 0
    authorization.AUTHORIZATION_EVENT_LOG.clear()
    authorization._EVENT_INDEX.clear()
    checkins._STORE.clear()
    checkins._AUDIT.clear()
    import app.main as m

    m._TABLES["rooms"].clear()
    m._TABLES["bookings"].clear()
    m._TABLES["payments"].clear()
    m._TABLES["devices"].clear()
    m._TABLES["commands"].clear()
    m._TABLES["telemetry"].clear()
    m._TABLES["alerts"].clear()
    m._COMMAND_COUNTER = 0
    m._ALERT_COUNTER = 0
    m._BOOKING_COUNTER = 0
    m._PAYMENT_COUNTER = 0
    m._SEEDED = False


def iso(delta_hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=delta_hours)).isoformat()


# ---------------------------------------------------------------------------
# 1. Catalog, profile tiers and the RoomPower opt-in rule
# ---------------------------------------------------------------------------

def test_catalog_and_profiles() -> None:
    print("\n[catalog / profiles]")
    catalog = call("module_catalog_list")
    check("catalog lists modules", catalog["ok"] and len(catalog["modules"]) >= 6)
    hotel = call("module_profile_get", business_type="hotel")["profile"]
    by_id = {row["module_id"]: row for row in hotel}
    check("hotel profile has tiers", all(row["requirement"] in modules.PROFILE_TIERS for row in hotel))
    check("RoomPower is not auto-installed for a hotel", by_id["roompower"]["install"] is False)
    check("RoomPower is recommended, not required", by_id["roompower"]["requirement"] == "recommended")
    check("Bookings is required for a hotel", by_id["bookings"]["requirement"] == "required")

    boot = call("module_bootstrap", business_id="biz-h1", business_type="hotel")
    check("bootstrap installs bookings", any(r["module_id"] == "bookings" for r in boot["installed"]))
    surface = call("module_surface", business_id="biz-h1")["surface"]
    check("surface is configured", surface["configured"] is True)
    check("surface nav excludes RoomPower before opt-in",
          "roompower" not in [n["module_id"] for n in surface["nav"]])
    check("surface nav includes enabled modules",
          set(["bookings", "quickpass", "propertyops"]).issubset(surface["enabled"]))


# ---------------------------------------------------------------------------
# 2. Dependencies: enable/disable rules, config survives, reactivation
# ---------------------------------------------------------------------------

def test_dependencies_and_lifecycle() -> None:
    print("\n[dependencies / lifecycle]")
    call("module_bootstrap", business_id="biz-h2", business_type="hotel")

    # guesthub is installed but disabled by the profile. Take quickpass away
    # and guesthub can no longer be switched on.
    call("module_disable", business_id="biz-h2", module_id="quickpass")
    blocked = call("module_enable", business_id="biz-h2", module_id="guesthub")
    check("guesthub cannot be enabled without quickpass", blocked["ok"] is False, blocked)
    check("block names the missing module", blocked.get("missing") == ["quickpass"], blocked.get("missing"))

    # Bring quickpass back, enable guesthub, then try to remove quickpass.
    call("module_enable", business_id="biz-h2", module_id="quickpass")
    call("module_enable", business_id="biz-h2", module_id="guesthub")
    refused = call("module_disable", business_id="biz-h2", module_id="quickpass")
    check("quickpass cannot be disabled while guesthub is enabled", refused["ok"] is False)

    # Config and history survive a disable / re-enable cycle.
    call("module_config_set", business_id="biz-h2", module_id="quickpass", key="pass_ttl", value=42)
    call("module_disable", business_id="biz-h2", module_id="guesthub")
    disabled = call("module_disable", business_id="biz-h2", module_id="quickpass")
    check("quickpass disables once nothing requires it", disabled["ok"] is True)
    check("disable keeps the config row",
          call("module_config_get", business_id="biz-h2", module_id="quickpass", key="pass_ttl")["config"] is not None)

    events = call("module_events", business_id="biz-h2", module_id="quickpass")["events"]
    check("disable is recorded in the event log", any(e.get("action") == "disabled" for e in events))

    re_enabled = call("module_enable", business_id="biz-h2", module_id="quickpass")
    check("quickpass reactivates", re_enabled["ok"] is True)
    cfg = call("module_config_get", business_id="biz-h2", module_id="quickpass", key="pass_ttl")["config"]
    check("reactivation preserved the config value", cfg.get("value") == 42, cfg)
    events = call("module_events", business_id="biz-h2", module_id="quickpass")["events"]
    check("reactivation is recorded", any(e.get("action") == "reactivated" for e in events))

    dep = call("module_dependency_check", business_id="biz-h2", module_id="roompower")["dependencies"]
    check("RoomPower depends on the platform capability, not QuickPass",
          dep["requires"] == [] and "authorization" in dep["platform"])


# ---------------------------------------------------------------------------
# 3. Migration safety and tenant isolation
# ---------------------------------------------------------------------------

def test_migration_and_tenants() -> None:
    print("\n[migration / tenants]")
    # A business with no business_modules rows is legacy: nothing is gated.
    legacy = call("module_surface", business_id="biz-legacy")
    check("unconfigured business is not gated", legacy["surface"]["configured"] is False)
    check("legacy business can still list inventory", call("inventory_list")["ok"] is True)

    call("authorize_room_activation", business_id="biz-a", room_code="ROOM-204",
         source="pms", issued_by="tester")
    a = call("authorization_effective", business_id="biz-a", room_code="ROOM-204")
    b = call("authorization_effective", business_id="biz-b", room_code="ROOM-204")
    check("grant is effective for its tenant", a["authorization"]["authorized"] is True)
    check("grant does not leak across tenants", b["authorization"]["authorized"] is False)

    blocked = call("dispatch_activation", business_id="biz-a", room_code="ROOM-999",
                   device_code="VDEV-X")
    check("dispatch refuses a room with no grant", blocked["ok"] is False)


# ---------------------------------------------------------------------------
# 4. Authorization contract: dedupe, revocation, expiry, stale event
# ---------------------------------------------------------------------------

def test_authorization_contract() -> None:
    print("\n[authorization contract]")
    event = {
        "event_id": "EV-DUP-1",
        "business_id": "biz-c",
        "room_code": "ROOM-101",
        "authorization_type": "room_activation",
        "status": "granted",
        "source": "pms",
        "issued_by": "tester",
        "issued_at": iso(0),
        "expires_at": iso(4),
    }
    first = call("authorization_ingest", business_id="biz-c", event=event)
    second = call("authorization_ingest", business_id="biz-c", event=event)
    check("first ingestion creates an event", first["ok"] and first["created"] is True)
    check("duplicate event is deduplicated", second.get("duplicate") is True)
    check("duplicate did not append a second event",
          len(call("authorization_event_list", business_id="biz-c")["events"]) == 1)

    stale = call("dispatch_activation", business_id="biz-c", room_code="ROOM-101",
                 device_code="AZ3166-01", event_id="EV-OLD")
    check("stale event id cannot activate a room", stale["ok"] is False)

    expired = dict(event, event_id="EV-EXPIRED", expires_at=iso(-1))
    call("authorization_ingest", business_id="biz-c", event=expired)
    eff = call("authorization_effective", business_id="biz-c", room_code="ROOM-101")
    check("expired grant is not effective", eff["authorization"]["authorized"] is False)
    check("expiry reason is reported", eff["authorization"]["reason"] in ("expired", "no_authorization_event", "revoked"))

    call("revoke_room_activation", business_id="biz-c", room_code="ROOM-101")
    eff = call("authorization_effective", business_id="biz-c", room_code="ROOM-101")
    check("revocation ends the grant", eff["authorization"]["authorized"] is False)

    wrong_tenant = dict(event, event_id="EV-OTHER", business_id="biz-zzz")
    rejected = call("authorization_ingest", business_id="biz-c", event=wrong_tenant)
    check("event for another tenant is rejected", rejected["ok"] is False)


# ---------------------------------------------------------------------------
# 5. Command lifecycle
# ---------------------------------------------------------------------------

def test_command_lifecycle() -> None:
    print("\n[command lifecycle]")
    call("get_status")  # seeds the demo devices
    call("module_bootstrap", business_id="biz-d", business_type="hotel")
    call("module_install", business_id="biz-d", module_id="roompower", enabled=True)

    queued = call("queue_command", device_code="AZ3166-01", command="POWER_ON",
                  business_id="biz-d", room_code=None)
    # queue_command via the action does not pass a business; issue through the
    # gated dispatch surface instead so the command is owned by the tenant.
    call("authorize_room_activation", business_id="biz-d", room_code="ROOM-204",
         source="pms", issued_by="tester")
    result = call("dispatch_activation", business_id="biz-d", room_code="ROOM-204",
                  device_code="AZ3166-01")
    check("dispatch queues a PENDING command", result["ok"] and result["command"]["status"] == commands.PENDING)
    check("command records the authorization event",
          result["command"]["authorization_event_id"] is not None)
    check("dispatch does not claim the room is live", "not live" in result["note"])

    again = call("dispatch_activation", business_id="biz-d", room_code="ROOM-204",
                 device_code="AZ3166-01")
    check("repeated dispatch is idempotent",
          again["command"]["command_id"] == result["command"]["command_id"]
          and again["command"].get("deduplicated") is True)

    cmd_id = result["command"]["command_id"]
    acked_before_sent = call("device_ack", command_id=cmd_id, device_code="AZ3166-01",
                             reported_relay_state="ON")
    check("acknowledgement is accepted by the lifecycle", acked_before_sent["ok"] is True)
    twice = call("device_ack", command_id=cmd_id, device_code="AZ3166-01",
                 reported_relay_state="ON")
    check("second acknowledgement is refused", twice["ok"] is False)
    state = call("device_state_get", business_id="biz-d", device_code="AZ3166-01")["device_state"]
    check("device state is recorded separately from command status",
          state["reported_state"]["relay"] == "ON" and state["command_id"] == cmd_id)

    wrong_device = call("device_ack", command_id=cmd_id, device_code="VDEV-101")
    check("ack from the wrong device is refused", wrong_device["ok"] is False)

    # Cancellation blocks a late acknowledgement.
    fresh = commands.queue("biz-d", "AZ3166-01", "POWER_OFF", room_code="ROOM-204")
    call("command_cancel", command_id=fresh["command_id"], reason="guest extended stay")
    late = call("device_ack", command_id=fresh["command_id"], device_code="AZ3166-01")
    check("cancelled command cannot be acknowledged", late["ok"] is False)

    # Expiry is driven by the scheduler action, not a background timer.
    expiring = commands.queue("biz-d", "AZ3166-01", "STATUS_REQUEST", room_code="ROOM-204")
    commands.COMMANDS[expiring["command_id"]]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    expired = call("command_expire", business_id="biz-d")["expired"]
    check("overdue command expires", any(c["command_id"] == expiring["command_id"] for c in expired))
    check("expired command cannot be sent",
          commands.mark_sent(expiring["command_id"])["ok"] is False)


# ---------------------------------------------------------------------------
# 6. Checkout energy policy
# ---------------------------------------------------------------------------

def test_checkout_policy() -> None:
    print("\n[checkout energy policy]")
    call("module_bootstrap", business_id="biz-e", business_type="hotel")
    call("module_install", business_id="biz-e", module_id="roompower", enabled=True)

    policy = call("checkout_policy_get", business_id="biz-e")["policy"]
    check("default policy cuts only non-essential circuits", policy["mode"] == "saving")
    check("blanket shutdown is off by default", policy["allow_blanket_shutdown"] is False)

    bad = call("checkout_policy_set", business_id="biz-e", policy={"mode": "nuke"})
    check("invalid policy mode is rejected", bad["ok"] is False)

    call("checkout_policy_set", business_id="biz-e",
         policy={"mode": "full_shutdown", "allow_blanket_shutdown": False, "grace_minutes": 0})
    call("authorize_room_activation", business_id="biz-e", room_code="ROOM-204",
         source="pms", issued_by="tester")
    out = call("dispatch_checkout", business_id="biz-e", room_code="ROOM-204",
               device_code="AZ3166-01")
    check("checkout revokes the grant", out["authorization_event"]["status"] == "revoked")
    check("full shutdown degrades to the saving policy",
          out["energy"]["action"] == "cut_non_essential"
          and out["energy"]["degraded_from_full_shutdown"] is True)
    check("essential circuits are preserved",
          "life_safety" in out["energy"]["keep_circuits"])
    check("checkout never queues a blanket POWER_OFF",
          out["command"]["command"] == "CUT_NON_ESSENTIAL")

    call("checkout_policy_set", business_id="biz-e", policy={"mode": "hold"})
    call("authorize_room_activation", business_id="biz-e", room_code="ROOM-101",
         source="pms", issued_by="tester")
    held = call("dispatch_checkout", business_id="biz-e", room_code="ROOM-101",
                device_code="VDEV-101")
    check("hold policy issues no command", held["command"] is None and held["energy"]["action"] == "hold")


# ---------------------------------------------------------------------------
# 7. The vertical slice: booking -> ... -> guest experience
# ---------------------------------------------------------------------------

def test_vertical_slice() -> None:
    print("\n[vertical slice]")
    call("module_bootstrap", business_id="biz-slice", business_type="hotel")
    call("module_install", business_id="biz-slice", module_id="roompower", enabled=True)
    call("module_config_set", business_id="biz-slice", module_id="roompower",
         key="checkout_policy",
         value={"mode": "saving", "grace_minutes": 0, "essential_circuits": ["life_safety"],
                "allow_blanket_shutdown": False})

    inventory = call("inventory_list")
    check("inventory is seeded", inventory["ok"] and inventory["count"] >= 3, inventory)

    # Clear the demo stays so the slice runs against a genuinely free room.
    for existing in call("booking_list", status="confirmed")["bookings"]:
        call("cancel_booking", booking_id=existing["booking_id"])

    booking = call("booking_create", room_code="ROOM-204", guest_label="Ada Lovelace",
                   start_at=iso(-1), end_at=iso(24))
    check("booking is created", booking["ok"] and booking["booking_id"])
    booking_id = booking["booking_id"]

    overlap = call("booking_create", room_code="ROOM-204", guest_label="Grace Hopper",
                   start_at=iso(1), end_at=iso(5))
    check("overlapping booking is rejected", overlap["ok"] is False)

    flow = call("booking_flow", booking_id=booking_id, business_id="biz-slice")
    check("flow stops at payment before payment is confirmed",
          flow["blocked_at"] == "payment_confirmed", flow["blocked_at"])

    paid = call("confirm_payment", payment_id=booking["payment_id"])
    check("payment is confirmed", paid["ok"] and paid["payment_status"] == "confirmed")

    arrived = call("check_in_create", business_id="biz-slice", booking_id=booking_id,
                   room_code="ROOM-204", guest_label="Ada Lovelace", actor_id="desk-1")
    check("check-in is created", arrived["ok"])
    call("check_in_verify", business_id="biz-slice", booking_id=booking_id, actor_id="desk-1")
    flow = call("booking_flow", booking_id=booking_id, business_id="biz-slice")
    check("flow waits for receptionist approval", flow["blocked_at"] == "receptionist_approved")

    approved = call("check_in_approve", business_id="biz-slice", booking_id=booking_id,
                    actor_id="desk-1")
    check("approval issues the authorization event",
          approved["ok"] and approved["authorization_event"]["status"] == "granted")
    check("grant is effective for the room", approved["authorization"]["authorized"] is True)

    activated = call("check_in_activate", business_id="biz-slice", booking_id=booking_id,
                     actor_id="desk-1", device_code="AZ3166-01")
    check("activation queues a command", activated["ok"] and activated["dispatched_command"])
    check("activation is authorized, not assumed",
          activated["authorization_event_id"] == approved["authorization_event"]["event_id"])

    polled = call("device_poll", device_code="AZ3166-01")
    check("device receives the command as SENT", polled["ok"] and polled["command"]["status"] == commands.SENT)
    acked = call("device_ack", command_id=polled["command"]["command_id"],
                 device_code="AZ3166-01", reported_relay_state="ON")
    check("device acknowledges", acked["ok"] and acked["reported_relay_state"] == "ON")

    flow = call("booking_flow", booking_id=booking_id, business_id="biz-slice")
    check("the whole guest journey is complete", flow["complete"] is True,
          [s["stage"] for s in flow["stages"] if not s["ok"]])

    stayed = call("check_in_check_out", business_id="biz-slice", booking_id=booking_id,
                  actor_id="desk-1")
    check("checkout succeeds", stayed["ok"])
    check("checkout applies the energy policy",
          (stayed.get("energy") or {}).get("action") == "cut_non_essential")
    after = call("authorization_effective", business_id="biz-slice", room_code="ROOM-204")
    check("checkout revoked the grant", after["authorization"]["authorized"] is False)
    reopened = call("booking_flow", booking_id=booking_id, business_id="biz-slice")
    check("flow reports the revoked authorization",
          reopened["blocked_at"] == "authorization_granted")


# ---------------------------------------------------------------------------
# 8. Route guard: a module the business has not enabled is not on the surface
# ---------------------------------------------------------------------------

def test_route_guard() -> None:
    print("\n[route guard]")
    call("module_bootstrap", business_id="biz-r", business_type="hotel")
    surface = call("module_surface", business_id="biz-r")["surface"]
    check("RoomPower route is not offered", "roompower" not in [n["module_id"] for n in surface["nav"]])
    gated = call("command_list", business_id="biz-r")
    check("RoomPower action is gated server-side", gated["ok"] is False and gated.get("module_disabled") is True)

    call("module_install", business_id="biz-r", module_id="roompower", enabled=True)
    surface = call("module_surface", business_id="biz-r")["surface"]
    check("RoomPower route appears after install and enable",
          "roompower" in [n["module_id"] for n in surface["nav"]])
    check("RoomPower action is allowed after enable", call("command_list", business_id="biz-r")["ok"] is True)

    call("module_disable", business_id="biz-r", module_id="roompower")
    check("disabling hides the route again",
          "roompower" not in [n["module_id"] for n in call("module_surface", business_id="biz-r")["surface"]["nav"]])
    check("disabling keeps the installed row",
          any(m["module_id"] == "roompower" and m["installed"] and not m["enabled"]
              for m in call("module_surface", business_id="biz-r")["surface"]["modules"]))


def test_access_control() -> None:
    print("\n[access control]")
    from app import roles

    # The matrix: who holds what, and who does not.
    check("owner holds every permission",
          roles.permissions_for("owner") == sorted(roles.PERMISSIONS))
    check("front desk may approve a check-in",
          roles.role_may("front_desk", "checkin.approve"))
    check("front desk may not manage staff",
          not roles.role_may("front_desk", "staff.manage"))
    check("housekeeping may not confirm a payment",
          not roles.role_may("housekeeping", "payments.record"))
    check("maintenance may queue a device command",
          roles.role_may("maintenance", "devices.command"))
    check("housekeeping may not queue a device command",
          not roles.role_may("housekeeping", "devices.command"))
    check("an unidentified caller holds nothing",
          roles.permissions_for("") == []
          and not roles.role_may("", "bookings.write"))
    check("role aliases normalise (frontdesk -> front_desk)",
          roles.role_may("FrontDesk", "checkin.approve"))

    # Enforcement at dispatch: a mutating action refuses loudly.
    denied = call("confirm_payment", booking_id="B-1")
    check("an unidentified caller is refused a mutating action",
          denied.get("ok") is False and denied.get("refused") is True
          and "access control" in denied.get("error", ""))
    under_privileged = call("staff_add", name="X", actor_role="housekeeping")
    check("an under-privileged role is refused",
          under_privileged.get("ok") is False
          and under_privileged.get("refused") is True
          and under_privileged.get("role") == "housekeeping")
    allowed = call("confirm_payment", booking_id="B-1", actor_role="front_desk")
    check("front desk passes the gate and reaches the action"
          " (its own validation answers)",
          "refused" not in allowed)

    # The staff actions behind staff.manage.
    added = call("staff_add", name="Ada Okonkwo", email="ada@powerpeg.dev",
                 role="front_desk")
    member = added.get("staff_member") or {}
    check("staff_add records the member with the named role",
          added.get("ok") is True and member.get("role") == "front_desk")
    bad_role = call("staff_add", name="X", role="chief")
    check("an unknown role is refused, not silently granted",
          bad_role.get("ok") is False and "unknown role" in bad_role.get("error", ""))
    removed = call("staff_remove", staff_member_id=member.get("staff_member_id"))
    check("staff_remove takes the member off the list",
          removed.get("ok") is True)
    gone = call("staff_remove", staff_member_id=member.get("staff_member_id"))
    check("removing twice fails honestly",
          gone.get("ok") is False)

    # The catalog action is an open read.
    cat = call("roles_catalog")
    check("roles_catalog names the roles and permissions",
          cat.get("ok") is True and "owner" in (cat.get("roles") or {})
          and "checkin.approve" in (cat.get("permissions") or {}))


def test_hook_dispatch_by_table() -> None:
    print("\n[hooks route on the context's table]")
    # The platform's hook envelope carries the row's data keyed by column
    # id and names the saved table in the context — not in the payload.
    columns = [
        {"id": "col-status", "name": "status"},
        {"id": "col-session", "name": "session_id"},
        {"id": "col-provider", "name": "provider"},
    ]
    context = {"table": {"name": "verifications", "columns": columns}}
    result = main(context, {"col-status": "verified",
                            "col-session": "demo-1",
                            "col-provider": "demo"})
    check("context table routes to the verification hook",
          result.get("ok") is True and result.get("status") == "verified")

    refused = main(context, {"col-status": "verified", "col-session": ""})
    check("hook refusals survive the id-to-name rename",
          refused.get("ok") is False and refused.get("refused") is True)

    ignored = main({"table": {"name": "no_such_table"}}, {"anything": 1})
    check("an unhooked table falls through to the action dispatcher",
          ignored.get("ok") is False and "no action supplied"
          in ignored.get("error", ""))

    # A payload that already names its keys (custom string column ids)
    # passes through the rename unchanged.
    named = main(context, {"status": "pending", "session_id": ""})
    check("already-named keys are kept", named.get("ok") is True)


def test_unknown_action() -> None:
    print("\n[dispatch hygiene]")
    result = call("no_such_action")
    check("unknown action fails loudly", result["ok"] is False and "unknown action" in result["error"])


def run() -> int:
    tests = [
        test_catalog_and_profiles,
        test_dependencies_and_lifecycle,
        test_migration_and_tenants,
        test_authorization_contract,
        test_command_lifecycle,
        test_checkout_policy,
        test_vertical_slice,
        test_access_control,
        test_route_guard,
        test_hook_dispatch_by_table,
        test_unknown_action,
    ]
    for test in tests:
        reset()
        test()
    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("Failed checks:")
        for name in FAILED:
            print(f"  - {name}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(run())
