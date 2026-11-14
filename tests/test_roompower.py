"""RoomPower's guard: what may be dispatched, and what the twin reports.

These test the decisions, not the widgets. The command guard is the part of
RoomPower that must never be wrong, because it is the only thing standing
between "a booking exists" and "a room is live".
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "function"))

from app import roompower  # noqa: E402
from app.authorization import (  # noqa: E402
    authorize_room_activation,
    effective_authorization,
    revoke_room_activation,
)

BID = "biz-roompower-test"
ROOM = "ROOM-204"
DEVICE = "AZ3166-01"


def _power_on(**overrides):
    row = {
        "command": "POWER_ON",
        "device_code": DEVICE,
        "room_code": ROOM,
        "business_id": BID,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Admission
# ---------------------------------------------------------------------------

def test_power_on_is_refused_without_a_grant():
    result = roompower.decide_command(BID, _power_on())
    assert result["ok"] is False
    assert result["reason"] == "no_authorization_event"
    assert "grant" in result["error"]


def test_power_on_is_admitted_once_core_grants_the_room():
    room = "ROOM-GRANTED"
    event = authorize_room_activation(BID, room, issued_by="reception")
    result = roompower.decide_command(BID, _power_on(room_code=room))
    assert result["ok"] is True
    assert result["row"]["status"] == "PENDING"
    assert result["row"]["authorization_event_id"] == event["event_id"]


def test_power_on_is_refused_again_after_revocation():
    room = "ROOM-REVOKED"
    authorize_room_activation(BID, room, issued_by="reception")
    revoke_room_activation(BID, room, issued_by="reception")
    result = roompower.decide_command(BID, _power_on(room_code=room))
    assert result["ok"] is False
    assert result["reason"] == "revoked"


def test_power_on_is_refused_when_the_grant_has_expired():
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    authorize_room_activation(BID, "ROOM-EXPIRED", expires_at=past)
    result = roompower.decide_command(
        BID, _power_on(room_code="ROOM-EXPIRED")
    )
    assert result["ok"] is False
    assert result["reason"] == "expired"


def test_unknown_command_is_refused():
    result = roompower.decide_command(BID, _power_on(command="OPEN_DOOR"))
    assert result["ok"] is False
    assert result["reason"] == "unknown_command"


def test_command_without_a_device_is_refused():
    result = roompower.decide_command(BID, _power_on(device_code=""))
    assert result["ok"] is False
    assert result["reason"] == "missing_device"


def test_a_saved_row_cannot_claim_to_be_acknowledged():
    """The row is normalised, so a browser cannot write its own success."""
    room = "ROOM-NORMALISED"
    authorize_room_activation(BID, room, issued_by="reception")
    result = roompower.decide_command(
        BID,
        _power_on(room_code=room, status="ACKNOWLEDGED",
                  acknowledged_at="2026-01-01"),
    )
    assert result["ok"] is True
    assert result["row"]["status"] == "PENDING"
    assert result["row"]["acknowledged_at"] is None


def test_power_off_needs_no_grant():
    """Cutting power is always allowed; that is the safe direction."""
    result = roompower.decide_command(
        BID, _power_on(command="POWER_OFF")
    )
    assert result["ok"] is True


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def test_relay_on_without_a_grant_is_an_unauthorized_load():
    result = roompower.reconcile_device(
        BID,
        {"device_code": DEVICE, "reported_relay_state": "ON"},
        room_code="ROOM-NEVER-GRANTED",
    )
    assert result["state"] == "unauthorized_load"
    assert result["authorized"] is False


def test_relay_on_with_a_grant_is_live():
    room = "ROOM-LIVE"
    authorize_room_activation(BID, room, issued_by="reception")
    result = roompower.reconcile_device(
        BID, {"device_code": DEVICE, "reported_relay_state": "ON"},
        room_code=room,
    )
    assert result["state"] == "live"


def test_relay_off_with_a_grant_is_a_state_mismatch():
    room = "ROOM-MISMATCH"
    authorize_room_activation(BID, room, issued_by="reception")
    result = roompower.reconcile_device(
        BID, {"device_code": DEVICE, "reported_relay_state": "OFF"},
        room_code=room,
    )
    assert result["state"] == "state_mismatch"
    assert result["authorized"] is True


def test_relay_off_without_a_grant_is_simply_off():
    result = roompower.reconcile_device(
        BID,
        {"device_code": DEVICE, "reported_relay_state": "OFF"},
        room_code="ROOM-IDLE",
    )
    assert result["state"] == "off"
    assert result["authorized"] is False


# ---------------------------------------------------------------------------
# Hooks and acknowledgement
# ---------------------------------------------------------------------------

def test_command_hook_refuses_and_says_why():
    hook = roompower.on_command_post_save(_power_on())
    assert hook["ok"] is False
    assert hook["refused"] is True
    assert "grant" in hook["error"]


def test_command_hook_queues_an_admitted_command_in_the_lifecycle():
    room = "ROOM-QUEUED"
    authorize_room_activation(BID, room, issued_by="reception")
    hook = roompower.on_command_post_save(_power_on(room_code=room))
    assert hook["ok"] is True
    assert hook["command"]["status"] == "PENDING"
    assert hook["queued_lifecycle"] is True


def test_device_hook_reports_the_anomaly_rather_than_hiding_it():
    hook = roompower.on_device_post_save(
        {"business_id": BID, "device_code": DEVICE, "room_code": "ROOM-ROGUE",
         "reported_relay_state": "ON"}
    )
    assert hook["ok"] is True
    assert hook["state"] == "unauthorized_load"
    assert hook["alert"] is True


def test_twin_acknowledgement_closes_the_command():
    room = "ROOM-ACKED"
    authorize_room_activation(BID, room, issued_by="reception")
    hook = roompower.on_command_post_save(_power_on(room_code=room))
    command_id = hook["command"]["command_id"]

    ack = roompower.acknowledge(
        command_id, DEVICE, "ON", business_id=BID, room_code=room
    )
    assert ack["ok"] is True
    assert ack["command"]["status"] == "ACKNOWLEDGED"
    assert ack["command"]["device_reported_state"] == {"relay": "ON"}
    assert ack["reconciliation"]["state"] == "live"
