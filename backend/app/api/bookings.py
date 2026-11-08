from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import Booking, Payment, Room, utc_now
from app.schemas.schemas import BookingCreate, BookingResponse, PaymentUpdate, PaymentResponse
from app.services.audit_service import record_audit_event
from app.services.auth_engine import AuthorisationEngine

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(booking_in: BookingCreate, db: AsyncSession = Depends(get_db)):
    room_stmt = select(Room).where(Room.id == booking_in.room_id)
    room_res = await db.execute(room_stmt)
    room = room_res.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    booking = Booking(
        room_id=booking_in.room_id,
        guest_label=booking_in.guest_label,
        start_at=booking_in.start_at,
        end_at=booking_in.end_at,
        booking_status=booking_in.booking_status,
        created_by="admin",
        created_at=utc_now()
    )
    db.add(booking)
    await db.flush()

    payment = Payment(
        booking_id=booking.id,
        payment_status="pending",
        amount=150.0,
        is_simulated=True,
        updated_by="admin",
        updated_at=utc_now()
    )
    db.add(payment)
    await db.flush()

    await record_audit_event(
        db=db,
        actor_type="ADMIN",
        actor_id="admin",
        event_type="BOOKING_CREATED",
        target_type="BOOKING",
        target_id=str(booking.id),
        details={
            "room_id": booking.room_id,
            "guest_label": booking.guest_label,
            "start_at": booking.start_at.isoformat(),
            "end_at": booking.end_at.isoformat()
        }
    )

    await db.commit()
    await db.refresh(booking)
    await db.refresh(payment)

    await AuthorisationEngine.evaluate_room(db, booking.room_id, actor_id="admin")
    await db.commit()

    return BookingResponse(
        id=booking.id,
        room_id=booking.room_id,
        guest_label=booking.guest_label,
        start_at=booking.start_at,
        end_at=booking.end_at,
        booking_status=booking.booking_status,
        created_by=booking.created_by,
        created_at=booking.created_at,
        payment=PaymentResponse.model_validate(payment)
    )

@router.patch("/{booking_id}/payment", response_model=PaymentResponse)
async def update_payment_status(booking_id: int, pay_in: PaymentUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Payment).where(Payment.booking_id == booking_id)
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    old_status = payment.payment_status
    payment.payment_status = pay_in.payment_status.lower()
    if pay_in.amount is not None:
        payment.amount = pay_in.amount
    payment.updated_at = utc_now()
    payment.updated_by = "admin"
    await db.flush()

    await record_audit_event(
        db=db,
        actor_type="ADMIN",
        actor_id="admin",
        event_type="PAYMENT_STATUS_CHANGED",
        target_type="PAYMENT",
        target_id=str(payment.id),
        details={"booking_id": booking_id, "previous_status": old_status, "new_status": payment.payment_status}
    )

    b_stmt = select(Booking).where(Booking.id == booking_id)
    b_res = await db.execute(b_stmt)
    booking = b_res.scalar_one_or_none()

    await db.commit()
    await db.refresh(payment)

    if booking:
        await AuthorisationEngine.evaluate_room(db, booking.room_id, actor_id="admin")
        await db.commit()

    return PaymentResponse.model_validate(payment)

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Booking).where(Booking.id == booking_id)
    res = await db.execute(stmt)
    booking = res.scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.booking_status = "cancelled"
    await db.flush()

    await record_audit_event(
        db=db,
        actor_type="ADMIN",
        actor_id="admin",
        event_type="BOOKING_CANCELLED",
        target_type="BOOKING",
        target_id=str(booking.id),
        details={"room_id": booking.room_id, "guest_label": booking.guest_label}
    )

    await db.commit()
    await db.refresh(booking)

    await AuthorisationEngine.evaluate_room(db, booking.room_id, actor_id="admin")
    await db.commit()

    pay_stmt = select(Payment).where(Payment.booking_id == booking.id)
    pay_res = await db.execute(pay_stmt)
    payment = pay_res.scalar_one_or_none()

    return BookingResponse(
        id=booking.id,
        room_id=booking.room_id,
        guest_label=booking.guest_label,
        start_at=booking.start_at,
        end_at=booking.end_at,
        booking_status=booking.booking_status,
        created_by=booking.created_by,
        created_at=booking.created_at,
        payment=PaymentResponse.model_validate(payment) if payment else None
    )

@router.get("", response_model=List[BookingResponse])
async def list_bookings(db: AsyncSession = Depends(get_db)):
    stmt = select(Booking).order_by(Booking.created_at.desc())
    res = await db.execute(stmt)
    bookings = res.scalars().all()

    results = []
    for b in bookings:
        pay_stmt = select(Payment).where(Payment.booking_id == b.id)
        pay_res = await db.execute(pay_stmt)
        payment = pay_res.scalar_one_or_none()
        results.append(
            BookingResponse(
                id=b.id,
                room_id=b.room_id,
                guest_label=b.guest_label,
                start_at=b.start_at,
                end_at=b.end_at,
                booking_status=b.booking_status,
                created_by=b.created_by,
                created_at=b.created_at,
                payment=PaymentResponse.model_validate(payment) if payment else None
            )
        )
    return results
