from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import AuditEvent, utc_now
from app.services.websocket_manager import ws_manager

async def record_audit_event(
    db: AsyncSession,
    actor_type: str,
    actor_id: str,
    event_type: str,
    target_type: str,
    target_id: str,
    details: Optional[Dict[str, Any]] = None
) -> AuditEvent:
    event = AuditEvent(
        actor_type=actor_type,
        actor_id=actor_id,
        event_type=event_type,
        target_type=target_type,
        target_id=str(target_id),
        details=details or {},
        created_at=utc_now()
    )
    db.add(event)
    await db.flush()

    await ws_manager.broadcast("AUDIT_EVENT", {
        "id": event.id,
        "actor_type": event.actor_type,
        "actor_id": event.actor_id,
        "event_type": event.event_type,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "details": event.details,
        "created_at": event.created_at.isoformat()
    })

    return event
