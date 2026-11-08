import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta, timezone
from app.main import app
from app.database import init_db
from app.services.seed_service import seed_data

@pytest.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    await seed_data()

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_end_to_end_authorisation_and_device_dispatch():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Fetch rooms, verify ROOM-204 is available and unauthorized
        rooms_res = await client.get("/api/rooms")
        assert rooms_res.status_code == 200
        rooms = rooms_res.json()
        room_204 = next(r for r in rooms if r["room"]["room_code"] == "ROOM-204")
        room_id = room_204["room"]["id"]
        device_id = room_204["device"]["id"]
        assert room_204["authorisation"]["authorised"] is False

        # 2. Create a booking for ROOM-204
        now = datetime.now(timezone.utc)
        booking_data = {
            "room_id": room_id,
            "guest_label": "Judge Demo Guest",
            "start_at": (now - timedelta(minutes=10)).isoformat(),
            "end_at": (now + timedelta(hours=2)).isoformat(),
            "booking_status": "confirmed"
        }
        b_res = await client.post("/api/bookings", json=booking_data)
        assert b_res.status_code == 201
        booking = b_res.json()
        booking_id = booking["id"]
        assert booking["payment"]["payment_status"] == "pending"

        # Check room status: still unauthorised because payment is pending!
        r_detail = (await client.get(f"/api/rooms/{room_id}")).json()
        assert r_detail["authorisation"]["authorised"] is False

        # 3. Confirm simulated payment
        pay_res = await client.patch(f"/api/bookings/{booking_id}/payment", json={"payment_status": "confirmed"})
        assert pay_res.status_code == 200
        assert pay_res.json()["payment_status"] == "confirmed"

        # Check room status: now AUTHORISED!
        r_detail2 = (await client.get(f"/api/rooms/{room_id}")).json()
        assert r_detail2["authorisation"]["authorised"] is True

        # 4. Device polls for next command
        cmd_res = await client.get(f"/api/devices/{device_id}/commands/next")
        assert cmd_res.status_code == 200
        command = cmd_res.json()
        assert command is not None
        assert command["command"] == "POWER_ON"
        assert command["status"] == "DELIVERED"
        cmd_id = command["id"]

        # 5. Device acknowledges command and reports simulated relay is ON
        ack_res = await client.post(
            f"/api/devices/{device_id}/commands/ack",
            json={
                "command_id": cmd_id,
                "status": "ACKNOWLEDGED",
                "reported_relay_state": "ON"
            }
        )
        assert ack_res.status_code == 200

        # Check device state
        dev_res = await client.get(f"/api/devices/{device_id}")
        assert dev_res.json()["reported_relay_state"] == "ON"

        # 6. Cancellation flow: Cancel booking -> revokes authorisation & queues POWER_OFF
        cancel_res = await client.post(f"/api/bookings/{booking_id}/cancel")
        assert cancel_res.status_code == 200
        r_detail3 = (await client.get(f"/api/rooms/{room_id}")).json()
        assert r_detail3["authorisation"]["authorised"] is False

        # Verify POWER_OFF is queued for AZ3166
        cmd_res2 = await client.get(f"/api/devices/{device_id}/commands/next")
        assert cmd_res2.status_code == 200
        off_cmd = cmd_res2.json()
        assert off_cmd["command"] == "POWER_OFF"

@pytest.mark.asyncio
async def test_anomaly_detection_rogue_energy_draw():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # ROOM-102 is unauthorized
        rooms = (await client.get("/api/rooms")).json()
        room_102 = next(r for r in rooms if r["room"]["room_code"] == "ROOM-102")
        room_id = room_102["room"]["id"]
        assert room_102["authorisation"]["authorised"] is False

        # Ingest simulated rogue power draw of 1.4 kW while unauthorized
        telem_data = {
            "room_id": room_id,
            "source": "SIMULATOR",
            "voltage": 230.0,
            "current": 6.1,
            "power": 1.4,
            "energy": 15.2,
            "is_simulated": True
        }
        telem_res = await client.post("/api/simulator/telemetry", json=telem_data)
        assert telem_res.status_code == 200

        # Verify Alert was raised
        alerts_res = await client.get("/api/alerts")
        alerts = alerts_res.json()
        rogue_alerts = [a for a in alerts if a["alert_type"] == "ENERGY_WHILE_UNAUTHORISED" and a["room_id"] == room_id]
        assert len(rogue_alerts) > 0
        alert_id = rogue_alerts[0]["id"]
        assert rogue_alerts[0]["status"] == "ACTIVE"
        assert rogue_alerts[0]["severity"] == "CRITICAL"

        # Acknowledge alert
        ack_res = await client.post(f"/api/alerts/{alert_id}/acknowledge", json={"acknowledged_by": "lead_engineer"})
        assert ack_res.status_code == 200
        assert ack_res.json()["status"] == "ACKNOWLEDGED"

@pytest.mark.asyncio
async def test_audit_timeline_recorded():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        audit_res = await client.get("/api/audit-events")
        assert audit_res.status_code == 200
        events = audit_res.json()
        assert len(events) > 0
        event_types = [e["event_type"] for e in events]
        assert "SYSTEM_INITIALIZED" in event_types
