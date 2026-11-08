from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import Room, Device, Booking, Payment, Authorisation, Telemetry, Alert
from app.schemas.schemas import (
    RoomCreate, RoomResponse, RoomDetailResponse, DeviceResponse, BookingResponse,
    PaymentResponse, AuthorisationResponse, TelemetryResponse, AlertResponse
)
from app.services.audit_service import record_audit_event
from app.services.auth_engine import AuthorisationEngine

router = APIRouter(prefix="/rooms", tags=["Rooms"])

@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(room_in: RoomCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Room).where(Room.room_code == room_in.room_code)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Room with code {room_in.room_code} already exists")

    room = Room(
        room_code=room_in.room_code,
        display_name=room_in.display_name,
        status=room_in.status,
        assigned_device_id=room_in.assigned_device_id
    )
    db.add(room)
    await db.flush()

    if room_in.assigned_device_id:
        dev_stmt = select(Device).where(Device.id == room_in.assigned_device_id)
        dev_res = await db.execute(dev_stmt)
        device = dev_res.scalar_one_or_none()
        if device:
            device.room_id = room.id
            await db.flush()

    await record_audit_event(
        db=db,
        actor_type="ADMIN",
        actor_id="admin",
        event_type="ROOM_CREATED",
        target_type="ROOM",
        target_id=str(room.id),
        details={"room_code": room.room_code, "display_name": room.display_name}
    )

    await db.commit()
    await db.refresh(room)

    await AuthorisationEngine.evaluate_room(db, room.id)
    await db.commit()

    return room

@router.get("", response_model=List[RoomDetailResponse])
async def list_rooms(db: AsyncSession = Depends(get_db)):
    stmt = select(Room)
    res = await db.execute(stmt)
    rooms = res.scalars().all()

    room_details = []
    for r in rooms:
        device_resp = None
        if r.assigned_device_id:
            dev_stmt = select(Device).where(Device.id == r.assigned_device_id)
            dev_res = await db.execute(dev_stmt)
            device = dev_res.scalar_one_or_none()
            if device:
                device_resp = DeviceResponse.model_validate(device)

        active_booking_resp = None
        b_stmt = select(Booking).where(Booking.room_id == r.id).order_by(Booking.id.desc()).limit(1)
        b_res = await db.execute(b_stmt)
        booking = b_res.scalar_one_or_none()
        if booking:
            pay_stmt = select(Payment).where(Payment.booking_id == booking.id)
            pay_res = await db.execute(pay_stmt)
            payment = pay_res.scalar_one_or_none()
            pay_resp = PaymentResponse.model_validate(payment) if payment else None
            active_booking_resp = BookingResponse(
                id=booking.id,
                room_id=booking.room_id,
                guest_label=booking.guest_label,
                start_at=booking.start_at,
                end_at=booking.end_at,
                booking_status=booking.booking_status,
                created_by=booking.created_by,
                created_at=booking.created_at,
                payment=pay_resp
            )

        auth_stmt = select(Authorisation).where(Authorisation.room_id == r.id).order_by(Authorisation.id.desc()).limit(1)
        auth_res = await db.execute(auth_stmt)
        auth = auth_res.scalar_one_or_none()
        auth_resp = AuthorisationResponse.model_validate(auth) if auth else None

        telem_stmt = select(Telemetry).where(Telemetry.room_id == r.id).order_by(Telemetry.id.desc()).limit(1)
        telem_res = await db.execute(telem_stmt)
        telem = telem_res.scalar_one_or_none()
        telem_resp = TelemetryResponse.model_validate(telem) if telem else None

        alert_stmt = select(Alert).where(Alert.room_id == r.id, Alert.status == "ACTIVE").order_by(Alert.id.desc())
        alert_res = await db.execute(alert_stmt)
        alerts = alert_res.scalars().all()
        alert_resps = [AlertResponse.model_validate(a) for a in alerts]

        room_details.append(
            RoomDetailResponse(
                room=RoomResponse.model_validate(r),
                device=device_resp,
                active_booking=active_booking_resp,
                authorisation=auth_resp,
                latest_telemetry=telem_resp,
                active_alerts=alert_resps
            )
        )

    return room_details

@router.get("/{room_id}", response_model=RoomDetailResponse)
async def get_room(room_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Room).where(Room.id == room_id)
    res = await db.execute(stmt)
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Room not found")

    device_resp = None
    if r.assigned_device_id:
        dev_stmt = select(Device).where(Device.id == r.assigned_device_id)
        dev_res = await db.execute(dev_stmt)
        device = dev_res.scalar_one_or_none()
        if device:
            device_resp = DeviceResponse.model_validate(device)

    active_booking_resp = None
    b_stmt = select(Booking).where(Booking.room_id == r.id).order_by(Booking.id.desc()).limit(1)
    b_res = await db.execute(b_stmt)
    booking = b_res.scalar_one_or_none()
    if booking:
        pay_stmt = select(Payment).where(Payment.booking_id == booking.id)
        pay_res = await db.execute(pay_stmt)
        payment = pay_res.scalar_one_or_none()
        pay_resp = PaymentResponse.model_validate(payment) if payment else None
        active_booking_resp = BookingResponse(
            id=booking.id,
            room_id=booking.room_id,
            guest_label=booking.guest_label,
            start_at=booking.start_at,
            end_at=booking.end_at,
            booking_status=booking.booking_status,
            created_by=booking.created_by,
            created_at=booking.created_at,
            payment=pay_resp
        )

    auth_stmt = select(Authorisation).where(Authorisation.room_id == r.id).order_by(Authorisation.id.desc()).limit(1)
    auth_res = await db.execute(auth_stmt)
    auth = auth_res.scalar_one_or_none()
    auth_resp = AuthorisationResponse.model_validate(auth) if auth else None

    telem_stmt = select(Telemetry).where(Telemetry.room_id == r.id).order_by(Telemetry.id.desc()).limit(1)
    telem_res = await db.execute(telem_stmt)
    telem = telem_res.scalar_one_or_none()
    telem_resp = TelemetryResponse.model_validate(telem) if telem else None

    alert_stmt = select(Alert).where(Alert.room_id == r.id, Alert.status == "ACTIVE").order_by(Alert.id.desc())
    alert_res = await db.execute(alert_stmt)
    alerts = alert_res.scalars().all()
    alert_resps = [AlertResponse.model_validate(a) for a in alerts]

    return RoomDetailResponse(
        room=RoomResponse.model_validate(r),
        device=device_resp,
        active_booking=active_booking_resp,
        authorisation=auth_resp,
        latest_telemetry=telem_resp,
        active_alerts=alert_resps
    )

@router.post("/{room_id}/assign-device", response_model=RoomResponse)
async def assign_device_to_room(room_id: int, device_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Room).where(Room.id == room_id)
    res = await db.execute(stmt)
    room = res.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    old_device_id = room.assigned_device_id
    room.assigned_device_id = device_id

    if device_id:
        dev_stmt = select(Device).where(Device.id == device_id)
        dev_res = await db.execute(dev_stmt)
        device = dev_res.scalar_one_or_none()
        if device:
            device.room_id = room_id

    if old_device_id and old_device_id != device_id:
        old_dev_stmt = select(Device).where(Device.id == old_device_id)
        old_dev_res = await db.execute(old_dev_stmt)
        old_device = old_dev_res.scalar_one_or_none()
        if old_device:
            old_device.room_id = None

    await record_audit_event(
        db=db,
        actor_type="ADMIN",
        actor_id="admin",
        event_type="DEVICE_ASSIGNED",
        target_type="ROOM",
        target_id=str(room.id),
        details={"previous_device_id": old_device_id, "new_device_id": device_id}
    )

    await db.commit()
    await db.refresh(room)
    return room
