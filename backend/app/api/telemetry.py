from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import Telemetry, Room, utc_now
from app.schemas.schemas import TelemetryIngest, TelemetryResponse
from app.services.simulator_service import simulator_service
from app.services.anomaly_service import AnomalyService
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["Telemetry & Simulator"])

@router.get("/rooms/{room_id}/telemetry", response_model=List[TelemetryResponse])
async def get_room_telemetry(room_id: int, limit: int = 60, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Telemetry)
        .where(Telemetry.room_id == room_id)
        .order_by(Telemetry.observed_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    telemetries = res.scalars().all()
    return list(reversed(telemetries))

@router.post("/simulator/telemetry", response_model=TelemetryResponse)
async def ingest_simulator_telemetry(data: TelemetryIngest, db: AsyncSession = Depends(get_db)):
    room_stmt = select(Room).where(Room.id == data.room_id)
    room_res = await db.execute(room_stmt)
    room = room_res.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    telemetry = Telemetry(
        room_id=data.room_id,
        source=data.source,
        voltage=data.voltage,
        current=data.current,
        power=data.power,
        energy=data.energy,
        is_simulated=True,
        observed_at=utc_now()
    )
    db.add(telemetry)
    await db.flush()

    await AnomalyService.check_telemetry_anomalies(db, telemetry)

    await db.commit()
    await db.refresh(telemetry)

    await ws_manager.broadcast("TELEMETRY_UPDATED", {
        "room_id": telemetry.room_id,
        "room_code": room.room_code,
        "voltage": telemetry.voltage,
        "current": telemetry.current,
        "power": telemetry.power,
        "energy": telemetry.energy,
        "is_simulated": True,
        "observed_at": telemetry.observed_at.isoformat()
    })

    return telemetry

@router.post("/simulator/rooms/{room_id}/injection")
async def set_simulator_injection(room_id: int, mode: str):
    allowed_modes = ["NORMAL", "FORCE_ROGUE_DRAW", "FORCE_ZERO"]
    if mode not in allowed_modes:
        raise HTTPException(status_code=400, detail=f"Mode must be one of {allowed_modes}")

    simulator_service.set_injection_mode(room_id, mode)
    return {"room_id": room_id, "injection_mode": mode, "status": "updated"}

@router.get("/simulator/rooms/{room_id}/status")
async def get_simulator_status(room_id: int):
    mode = simulator_service.get_injection_mode(room_id)
    state = simulator_service.get_or_init_room_state(room_id)
    return {
        "room_id": room_id,
        "injection_mode": mode,
        "accumulated_kwh": state["accumulated_kwh"],
        "is_simulated": True
    }
