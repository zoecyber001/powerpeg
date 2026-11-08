from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Room, Booking, Payment, Authorisation, Device, utc_now
from app.services.audit_service import record_audit_event
from app.services.device_service import DeviceService
from app.services.websocket_manager import ws_manager

class AuthorisationEngine:
    @staticmethod
    async def evaluate_room(
        db: AsyncSession, room_id: int, actor_id: str = "system"
    ) -> Tuple[Authorisation, bool]:
        now = utc_now()

        room_stmt = select(Room).where(Room.id == room_id)
        room_res = await db.execute(room_stmt)
        room = room_res.scalar_one_or_none()
        if not room:
            raise ValueError(f"Room {room_id} not found")

        auth_stmt = select(Authorisation).where(Authorisation.room_id == room_id).order_by(Authorisation.id.desc())
        auth_res = await db.execute(auth_stmt)
        auth = auth_res.scalar_one_or_none()

        booking_stmt = (
            select(Booking)
            .where(
                Booking.room_id == room_id,
                Booking.booking_status == "confirmed"
            )
            .order_by(Booking.start_at.desc())
        )
        booking_res = await db.execute(booking_stmt)
        bookings = booking_res.scalars().all()

        active_booking: Optional[Booking] = None
        eligible = False
        reason = "No active booking found"
        valid_from = None
        valid_until = None

        for b in bookings:
            b_start = b.start_at if b.start_at.tzinfo else b.start_at.replace(tzinfo=now.tzinfo)
            b_end = b.end_at if b.end_at.tzinfo else b.end_at.replace(tzinfo=now.tzinfo)

            if b_start <= now <= b_end:
                active_booking = b
                pay_stmt = select(Payment).where(Payment.booking_id == b.id)
                pay_res = await db.execute(pay_stmt)
                payment = pay_res.scalar_one_or_none()

                if payment and payment.payment_status == "confirmed":
                    eligible = True
                    reason = f"Confirmed booking ({b.guest_label}) with verified payment"
                    valid_from = b.start_at
                    valid_until = b.end_at
                elif payment and payment.payment_status == "pending":
                    reason = f"Booking exists ({b.guest_label}) but payment is PENDING"
                elif payment and payment.payment_status == "failed":
                    reason = f"Booking exists ({b.guest_label}) but payment FAILED"
                else:
                    reason = "Booking payment record missing"
                break
            elif now > b_end:
                reason = "Booking stay window expired"
            elif now < b_start:
                reason = "Booking stay window has not started yet"

        is_initial_eval = (auth is None)
        state_changed = is_initial_eval or (auth.authorised != eligible)

        if is_initial_eval:
            auth = Authorisation(
                room_id=room_id,
                booking_id=active_booking.id if active_booking else None,
                authorised=eligible,
                reason=reason,
                valid_from=valid_from,
                valid_until=valid_until,
                updated_at=now
            )
            db.add(auth)
        else:
            auth.authorised = eligible
            auth.booking_id = active_booking.id if active_booking else None
            auth.reason = reason
            auth.valid_from = valid_from
            auth.valid_until = valid_until
            auth.updated_at = now

        await db.flush()

        should_dispatch = (not is_initial_eval and state_changed) or (is_initial_eval and eligible)

        if should_dispatch:
            event_type = "ROOM_AUTHORISED" if eligible else "ROOM_UNAUTHORISED"
            await record_audit_event(
                db=db,
                actor_type="SYSTEM" if actor_id == "system" else "ADMIN",
                actor_id=actor_id,
                event_type=event_type,
                target_type="ROOM",
                target_id=str(room_id),
                details={"reason": reason, "authorised": eligible, "booking_id": active_booking.id if active_booking else None}
            )

            if room.assigned_device_id:
                command_name = "POWER_ON" if eligible else "POWER_OFF"
                await DeviceService.queue_command(
                    db=db,
                    device_id=room.assigned_device_id,
                    command_name=command_name,
                    actor_id=actor_id
                )

        await ws_manager.broadcast("AUTHORISATION_UPDATED", {
            "room_id": room_id,
            "authorised": auth.authorised,
            "reason": auth.reason,
            "valid_from": auth.valid_from.isoformat() if auth.valid_from else None,
            "valid_until": auth.valid_until.isoformat() if auth.valid_until else None,
            "updated_at": auth.updated_at.isoformat()
        })

        return auth, state_changed

    @staticmethod
    async def manual_override(
        db: AsyncSession, room_id: int, authorised: bool, reason: str, duration_minutes: int, actor_id: str = "admin"
    ) -> Authorisation:
        now = utc_now()
        valid_until = now + timedelta(minutes=duration_minutes)

        room_stmt = select(Room).where(Room.id == room_id)
        room_res = await db.execute(room_stmt)
        room = room_res.scalar_one_or_none()
        if not room:
            raise ValueError(f"Room {room_id} not found")

        auth_stmt = select(Authorisation).where(Authorisation.room_id == room_id).order_by(Authorisation.id.desc())
        auth_res = await db.execute(auth_stmt)
        auth = auth_res.scalar_one_or_none()

        override_reason = f"Manual override: {reason}"
        if not auth:
            auth = Authorisation(
                room_id=room_id,
                authorised=authorised,
                reason=override_reason,
                valid_from=now,
                valid_until=valid_until,
                updated_at=now
            )
            db.add(auth)
        else:
            auth.authorised = authorised
            auth.reason = override_reason
            auth.valid_from = now
            auth.valid_until = valid_until
            auth.updated_at = now

        await db.flush()

        await record_audit_event(
            db=db,
            actor_type="ADMIN",
            actor_id=actor_id,
            event_type="MANUAL_OVERRIDE",
            target_type="ROOM",
            target_id=str(room_id),
            details={"authorised": authorised, "reason": reason, "duration_minutes": duration_minutes}
        )

        if room.assigned_device_id:
            command_name = "POWER_ON" if authorised else "POWER_OFF"
            await DeviceService.queue_command(
                db=db,
                device_id=room.assigned_device_id,
                command_name=command_name,
                actor_id=actor_id
            )

        await ws_manager.broadcast("AUTHORISATION_UPDATED", {
            "room_id": room_id,
            "authorised": auth.authorised,
            "reason": auth.reason,
            "valid_from": auth.valid_from.isoformat(),
            "valid_until": auth.valid_until.isoformat(),
            "updated_at": auth.updated_at.isoformat()
        })

        return auth
