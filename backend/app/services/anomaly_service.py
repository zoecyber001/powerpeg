from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Alert, Room, Device, Authorisation, Telemetry, utc_now
from app.services.audit_service import record_audit_event
from app.services.websocket_manager import ws_manager
from app.config import settings

class AnomalyService:
    @staticmethod
    async def check_telemetry_anomalies(db: AsyncSession, telemetry: Telemetry) -> Optional[Alert]:
        room_stmt = select(Room).where(Room.id == telemetry.room_id)
        room_res = await db.execute(room_stmt)
        room = room_res.scalar_one_or_none()
        if not room:
            return None

        auth_stmt = select(Authorisation).where(Authorisation.room_id == room.id).order_by(Authorisation.id.desc())
        auth_res = await db.execute(auth_stmt)
        auth = auth_res.scalar_one_or_none()
        is_authorised = auth.authorised if auth else False

        if not is_authorised and telemetry.power > settings.UNAUTHORISED_ACTIVE_POWER_KW_THRESHOLD:
            existing_stmt = select(Alert).where(
                Alert.room_id == room.id,
                Alert.alert_type == "ENERGY_WHILE_UNAUTHORISED",
                Alert.status == "ACTIVE"
            )
            existing_res = await db.execute(existing_stmt)
            existing_alert = existing_res.scalar_one_or_none()

            if not existing_alert:
                alert = Alert(
                    room_id=room.id,
                    alert_type="ENERGY_WHILE_UNAUTHORISED",
                    severity="CRITICAL",
                    description=f"Rogue power draw detected: {telemetry.power:.2f} kW ({telemetry.current:.2f} A) in {room.room_code} while access is UNAUTHORISED.",
                    status="ACTIVE",
                    created_at=utc_now()
                )
                db.add(alert)
                await db.flush()

                await record_audit_event(
                    db=db,
                    actor_type="SYSTEM",
                    actor_id="anomaly_detector",
                    event_type="ENERGY_WHILE_UNAUTHORISED",
                    target_type="ALERT",
                    target_id=str(alert.id),
                    details={"room_id": room.id, "power": telemetry.power, "current": telemetry.current}
                )

                await ws_manager.broadcast("ALERT_RAISED", {
                    "id": alert.id,
                    "room_id": alert.room_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "description": alert.description,
                    "status": alert.status,
                    "created_at": alert.created_at.isoformat()
                })
                return alert

        return None

    @staticmethod
    async def check_device_state_mismatch(db: AsyncSession, device: Device) -> Optional[Alert]:
        if not device.room_id or device.connection_status != "online":
            return None

        auth_stmt = select(Authorisation).where(Authorisation.room_id == device.room_id).order_by(Authorisation.id.desc())
        auth_res = await db.execute(auth_stmt)
        auth = auth_res.scalar_one_or_none()
        is_authorised = auth.authorised if auth else False

        if is_authorised and device.reported_relay_state == "OFF":
            existing_stmt = select(Alert).where(
                Alert.room_id == device.room_id,
                Alert.alert_type == "DEVICE_STATE_MISMATCH",
                Alert.status == "ACTIVE"
            )
            existing_res = await db.execute(existing_stmt)
            existing_alert = existing_res.scalar_one_or_none()

            if not existing_alert:
                alert = Alert(
                    room_id=device.room_id,
                    alert_type="DEVICE_STATE_MISMATCH",
                    severity="WARNING",
                    description=f"Device {device.device_code} reports relay OFF, but room is AUTHORISED.",
                    status="ACTIVE",
                    created_at=utc_now()
                )
                db.add(alert)
                await db.flush()

                await record_audit_event(
                    db=db,
                    actor_type="SYSTEM",
                    actor_id="anomaly_detector",
                    event_type="DEVICE_STATE_MISMATCH",
                    target_type="ALERT",
                    target_id=str(alert.id),
                    details={"device_code": device.device_code, "reported_state": device.reported_relay_state}
                )

                await ws_manager.broadcast("ALERT_RAISED", {
                    "id": alert.id,
                    "room_id": alert.room_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "description": alert.description,
                    "status": alert.status,
                    "created_at": alert.created_at.isoformat()
                })
                return alert

        return None

    @staticmethod
    async def acknowledge_alert(db: AsyncSession, alert_id: int, acknowledged_by: str) -> Optional[Alert]:
        stmt = select(Alert).where(Alert.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if alert:
            alert.status = "ACKNOWLEDGED"
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = utc_now()
            await db.flush()

            await record_audit_event(
                db=db,
                actor_type="ADMIN",
                actor_id=acknowledged_by,
                event_type="ALERT_ACKNOWLEDGED",
                target_type="ALERT",
                target_id=str(alert.id),
                details={"alert_type": alert.alert_type, "room_id": alert.room_id}
            )

            await ws_manager.broadcast("ALERT_ACKNOWLEDGED", {
                "id": alert.id,
                "status": "ACKNOWLEDGED",
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": alert.acknowledged_at.isoformat()
            })

        return alert
