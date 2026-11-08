from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import AuditEvent, Room, Device, Alert, Authorisation
from app.schemas.schemas import (
    AuditEventResponse, AuthorisationResponse, ManualOverrideRequest
)
from app.services.auth_engine import AuthorisationEngine

router = APIRouter(tags=["Audit & Overview"])

@router.get("/audit-events", response_model=List[AuditEventResponse])
async def list_audit_events(limit: int = 100, db: AsyncSession = Depends(get_db)):
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    rooms_stmt = select(func.count(Room.id))
    rooms_count = (await db.execute(rooms_stmt)).scalar() or 0

    online_dev_stmt = select(func.count(Device.id)).where(Device.connection_status == "online")
    online_devices_count = (await db.execute(online_dev_stmt)).scalar() or 0

    total_dev_stmt = select(func.count(Device.id))
    total_devices_count = (await db.execute(total_dev_stmt)).scalar() or 0

    auth_stmt = select(func.count(Authorisation.id)).where(Authorisation.authorised == True)
    auth_count = (await db.execute(auth_stmt)).scalar() or 0

    alert_stmt = select(func.count(Alert.id)).where(Alert.status == "ACTIVE")
    active_alerts_count = (await db.execute(alert_stmt)).scalar() or 0

    return {
        "total_rooms": rooms_count,
        "authorised_rooms": auth_count,
        "unauthorised_rooms": max(0, rooms_count - auth_count),
        "devices_online": online_devices_count,
        "devices_total": total_devices_count,
        "active_alerts": active_alerts_count
    }

@router.post("/authorisations/evaluate")
async def evaluate_all_rooms(db: AsyncSession = Depends(get_db)):
    stmt = select(Room)
    res = await db.execute(stmt)
    rooms = res.scalars().all()
    results = []
    for r in rooms:
        auth, changed = await AuthorisationEngine.evaluate_room(db, r.id, actor_id="admin")
        results.append({"room_id": r.id, "authorised": auth.authorised, "changed": changed})
    await db.commit()
    return {"status": "success", "evaluations": results}

@router.post("/authorisations/override", response_model=AuthorisationResponse)
async def manual_override(override_in: ManualOverrideRequest, db: AsyncSession = Depends(get_db)):
    auth = await AuthorisationEngine.manual_override(
        db=db,
        room_id=override_in.room_id,
        authorised=override_in.authorised,
        reason=override_in.reason,
        duration_minutes=override_in.duration_minutes,
        actor_id="admin"
    )
    await db.commit()
    await db.refresh(auth)
    return auth
