from datetime import timedelta
from sqlalchemy import delete
from app.database import AsyncSessionLocal, init_db
from app.models.entities import (
    Room, Device, Booking, Payment, Authorisation, DeviceCommand, Telemetry, Alert, AuditEvent, utc_now
)
from app.services.auth_engine import AuthorisationEngine

async def seed_data():
    await init_db()

    async with AsyncSessionLocal() as db:
        await db.execute(delete(DeviceCommand))
        await db.execute(delete(Alert))
        await db.execute(delete(Telemetry))
        await db.execute(delete(Payment))
        await db.execute(delete(Booking))
        await db.execute(delete(Authorisation))
        await db.execute(delete(AuditEvent))
        await db.execute(delete(Room))
        await db.execute(delete(Device))
        await db.commit()

        now = utc_now()

        az3166 = Device(
            device_code="AZ3166-01",
            device_type="AZ3166",
            firmware_version="1.0.0",
            connection_status="online",
            reported_relay_state="OFF",
            last_seen_at=now,
            registered_at=now
        )
        db.add(az3166)
        await db.flush()

        vdev_101 = Device(
            device_code="VDEV-101",
            device_type="VIRTUAL",
            firmware_version="1.0.0",
            connection_status="online",
            reported_relay_state="ON",
            last_seen_at=now,
            registered_at=now
        )
        db.add(vdev_101)
        await db.flush()

        room_204 = Room(
            room_code="ROOM-204",
            display_name="Ocean View Deluxe 204",
            status="available",
            assigned_device_id=az3166.id
        )
        db.add(room_204)

        room_101 = Room(
            room_code="ROOM-101",
            display_name="Executive Suite 101",
            status="occupied",
            assigned_device_id=vdev_101.id
        )
        db.add(room_101)

        room_102 = Room(
            room_code="ROOM-102",
            display_name="Standard Double 102",
            status="available",
            assigned_device_id=None
        )
        db.add(room_102)

        await db.flush()

        az3166.room_id = room_204.id
        vdev_101.room_id = room_101.id
        await db.flush()

        booking_101 = Booking(
            room_id=room_101.id,
            guest_label="Marcus Vance (VIP)",
            start_at=now - timedelta(hours=3),
            end_at=now + timedelta(hours=21),
            booking_status="confirmed",
            created_by="frontdesk_sarah",
            created_at=now - timedelta(hours=4)
        )
        db.add(booking_101)
        await db.flush()

        payment_101 = Payment(
            booking_id=booking_101.id,
            payment_status="confirmed",
            amount=220.0,
            is_simulated=True,
            updated_by="frontdesk_sarah",
            updated_at=now - timedelta(hours=3, minutes=55)
        )
        db.add(payment_101)
        await db.flush()

        await AuthorisationEngine.evaluate_room(db, room_101.id)
        await AuthorisationEngine.evaluate_room(db, room_204.id)
        await AuthorisationEngine.evaluate_room(db, room_102.id)

        init_event = AuditEvent(
            actor_type="SYSTEM",
            actor_id="system",
            event_type="SYSTEM_INITIALIZED",
            target_type="SYSTEM",
            target_id="0",
            details={"demo_profile": "Hackathon Ready", "rooms": ["ROOM-204", "ROOM-101", "ROOM-102"]},
            created_at=now
        )
        db.add(init_event)

        await db.commit()
