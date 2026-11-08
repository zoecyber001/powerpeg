from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Device, DeviceCommand, Room, utc_now
from app.schemas.schemas import DeviceHeartbeat, DeviceCommandAck
from app.services.audit_service import record_audit_event
from app.services.websocket_manager import ws_manager
from app.config import settings

class DeviceService:
    @staticmethod
    async def register_device(
        db: AsyncSession, device_code: str, device_type: str = "AZ3166", room_id: Optional[int] = None, firmware_version: str = "1.0.0"
    ) -> Device:
        stmt = select(Device).where(Device.device_code == device_code)
        result = await db.execute(stmt)
        device = result.scalar_one_or_none()

        if not device:
            device = Device(
                device_code=device_code,
                device_type=device_type,
                room_id=room_id,
                firmware_version=firmware_version,
                connection_status="online",
                reported_relay_state="OFF",
                last_seen_at=utc_now()
            )
            db.add(device)
            await db.flush()

            await record_audit_event(
                db=db,
                actor_type="DEVICE",
                actor_id=device_code,
                event_type="DEVICE_REGISTERED",
                target_type="DEVICE",
                target_id=str(device.id),
                details={"device_code": device_code, "device_type": device_type, "room_id": room_id}
            )
        else:
            device.connection_status = "online"
            device.last_seen_at = utc_now()
            if room_id is not None:
                device.room_id = room_id
            if firmware_version:
                device.firmware_version = firmware_version
            await db.flush()

        if device.room_id:
            room_stmt = select(Room).where(Room.id == device.room_id)
            room_res = await db.execute(room_stmt)
            room = room_res.scalar_one_or_none()
            if room and room.assigned_device_id != device.id:
                room.assigned_device_id = device.id
                await db.flush()

        await ws_manager.broadcast("DEVICE_STATUS", {
            "id": device.id,
            "device_code": device.device_code,
            "connection_status": device.connection_status,
            "reported_relay_state": device.reported_relay_state,
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None
        })

        return device

    @staticmethod
    async def handle_heartbeat(db: AsyncSession, hb: DeviceHeartbeat) -> Device:
        stmt = select(Device).where(Device.device_code == hb.device_code)
        result = await db.execute(stmt)
        device = result.scalar_one_or_none()

        if not device:
            device = await DeviceService.register_device(
                db=db,
                device_code=hb.device_code,
                firmware_version=hb.firmware_version or "1.0.0"
            )

        was_offline = device.connection_status == "offline"
        device.connection_status = "online"
        device.last_seen_at = utc_now()
        device.reported_relay_state = hb.reported_relay_state.upper()
        if hb.firmware_version:
            device.firmware_version = hb.firmware_version

        await db.flush()

        if was_offline:
            await record_audit_event(
                db=db,
                actor_type="DEVICE",
                actor_id=device.device_code,
                event_type="DEVICE_RECONNECTED",
                target_type="DEVICE",
                target_id=str(device.id),
                details={"reported_relay_state": device.reported_relay_state}
            )

        await ws_manager.broadcast("DEVICE_HEARTBEAT", {
            "id": device.id,
            "device_code": device.device_code,
            "connection_status": device.connection_status,
            "reported_relay_state": device.reported_relay_state,
            "last_seen_at": device.last_seen_at.isoformat()
        })

        return device

    @staticmethod
    async def queue_command(db: AsyncSession, device_id: int, command_name: str, actor_id: str = "system") -> DeviceCommand:
        cmd = DeviceCommand(
            device_id=device_id,
            command=command_name,
            status="PENDING",
            issued_at=utc_now()
        )
        db.add(cmd)
        await db.flush()

        await record_audit_event(
            db=db,
            actor_type="SYSTEM" if actor_id == "system" else "ADMIN",
            actor_id=actor_id,
            event_type="DEVICE_COMMAND_ISSUED",
            target_type="DEVICE_COMMAND",
            target_id=str(cmd.id),
            details={"device_id": device_id, "command": command_name}
        )

        await ws_manager.broadcast("COMMAND_QUEUED", {
            "id": cmd.id,
            "device_id": device_id,
            "command": command_name,
            "status": "PENDING"
        })

        return cmd

    @staticmethod
    async def get_next_pending_command(db: AsyncSession, device_id: int) -> Optional[DeviceCommand]:
        stmt = (
            select(DeviceCommand)
            .where(DeviceCommand.device_id == device_id, DeviceCommand.status == "PENDING")
            .order_by(DeviceCommand.issued_at.asc())
            .limit(1)
        )
        result = await db.execute(stmt)
        cmd = result.scalar_one_or_none()

        if cmd:
            cmd.status = "DELIVERED"
            await db.flush()
        return cmd

    @staticmethod
    async def acknowledge_command(db: AsyncSession, ack: DeviceCommandAck) -> Optional[DeviceCommand]:
        stmt = select(DeviceCommand).where(DeviceCommand.id == ack.command_id)
        result = await db.execute(stmt)
        cmd = result.scalar_one_or_none()

        if cmd:
            cmd.status = ack.status
            cmd.acknowledged_at = utc_now()
            cmd.response_payload = ack.response_payload

            dev_stmt = select(Device).where(Device.id == cmd.device_id)
            dev_res = await db.execute(dev_stmt)
            device = dev_res.scalar_one_or_none()
            if device:
                device.reported_relay_state = ack.reported_relay_state.upper()
                device.last_seen_at = utc_now()
                device.connection_status = "online"

            await db.flush()

            await record_audit_event(
                db=db,
                actor_type="DEVICE",
                actor_id=device.device_code if device else str(cmd.device_id),
                event_type="DEVICE_COMMAND_ACKNOWLEDGED",
                target_type="DEVICE_COMMAND",
                target_id=str(cmd.id),
                details={
                    "command": cmd.command,
                    "status": ack.status,
                    "reported_relay_state": ack.reported_relay_state,
                    "response_payload": ack.response_payload
                }
            )

            await ws_manager.broadcast("COMMAND_ACKNOWLEDGED", {
                "id": cmd.id,
                "device_id": cmd.device_id,
                "command": cmd.command,
                "status": cmd.status,
                "reported_relay_state": ack.reported_relay_state
            })

        return cmd

    @staticmethod
    async def check_device_offline_timeouts(db: AsyncSession):
        threshold = utc_now() - timedelta(seconds=settings.DEVICE_HEARTBEAT_TIMEOUT_SECONDS)
        stmt = select(Device).where(Device.connection_status == "online", Device.last_seen_at < threshold)
        result = await db.execute(stmt)
        timed_out_devices = result.scalars().all()

        for dev in timed_out_devices:
            dev.connection_status = "offline"
            await record_audit_event(
                db=db,
                actor_type="SYSTEM",
                actor_id="heartbeat_monitor",
                event_type="DEVICE_OFFLINE",
                target_type="DEVICE",
                target_id=str(dev.id),
                details={"device_code": dev.device_code, "last_seen_at": dev.last_seen_at.isoformat() if dev.last_seen_at else None}
            )
            await ws_manager.broadcast("DEVICE_STATUS", {
                "id": dev.id,
                "device_code": dev.device_code,
                "connection_status": "offline",
                "reported_relay_state": dev.reported_relay_state
            })
        await db.flush()
