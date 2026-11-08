from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import Alert
from app.schemas.schemas import AlertResponse, AlertAcknowledge
from app.services.anomaly_service import AnomalyService

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertResponse])
async def list_alerts(status_filter: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Alert).order_by(Alert.created_at.desc())
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter.upper())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(alert_id: int, ack_in: AlertAcknowledge, db: AsyncSession = Depends(get_db)):
    alert = await AnomalyService.acknowledge_alert(
        db=db,
        alert_id=alert_id,
        acknowledged_by=ack_in.acknowledged_by
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.commit()
    await db.refresh(alert)
    return alert
