from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import Device, DeviceCommand
from app.schemas.schemas import (
    DeviceRegister, DeviceHeartbeat, DeviceCommandAck, DeviceResponse, DeviceCommandResponse
)
from app.services.device_service import DeviceService
from app.services.anomaly_service import AnomalyService

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.post("/register", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(dev_in: DeviceRegister, db: AsyncSession = Depends(get_db)):
    device = await DeviceService.register_device(
        db=db,
        device_code=dev_in.device_code,
        device_type=dev_in.device_type,
        room_id=dev_in.room_id,
        firmware_version=dev_in.firmware_version
    )
    await db.commit()
    await db.refresh(device)
    return device

@router.get("", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db)):
    stmt = select(Device).order_by(Device.id.asc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Device).where(Device.id == device_id)
    res = await db.execute(stmt)
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.post("/{device_id}/heartbeat", response_model=DeviceResponse)
async def device_heartbeat(device_id: int, hb: DeviceHeartbeat, db: AsyncSession = Depends(get_db)):
    stmt = select(Device).where(Device.id == device_id)
    res = await db.execute(stmt)
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    updated_device = await DeviceService.handle_heartbeat(db, hb)
    await AnomalyService.check_device_state_mismatch(db, updated_device)

    await db.commit()
    await db.refresh(updated_device)
    return updated_device

@router.get("/{device_id}/commands/next", response_model=Optional[DeviceCommandResponse])
async def get_next_command(device_id: int, db: AsyncSession = Depends(get_db)):
    cmd = await DeviceService.get_next_pending_command(db, device_id)
    if cmd:
        await db.commit()
        await db.refresh(cmd)
    return cmd

@router.post("/{device_id}/commands/ack", response_model=Optional[DeviceCommandResponse])
async def acknowledge_command(device_id: int, ack: DeviceCommandAck, db: AsyncSession = Depends(get_db)):
    cmd = await DeviceService.acknowledge_command(db, ack)
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")

    dev_stmt = select(Device).where(Device.id == device_id)
    dev_res = await db.execute(dev_stmt)
    device = dev_res.scalar_one_or_none()
    if device:
        await AnomalyService.check_device_state_mismatch(db, device)

    await db.commit()
    await db.refresh(cmd)
    return cmd

@router.post("/{device_id}/commands/manual", response_model=DeviceCommandResponse)
async def manual_command(device_id: int, command: str, db: AsyncSession = Depends(get_db)):
    cmd_name = command.upper()
    if cmd_name not in ["POWER_ON", "POWER_OFF", "STATUS_REQUEST"]:
        raise HTTPException(status_code=400, detail="Invalid command. Allowed: POWER_ON, POWER_OFF, STATUS_REQUEST")

    cmd = await DeviceService.queue_command(db, device_id, cmd_name, actor_id="admin")
    await db.commit()
    await db.refresh(cmd)
    return cmd
