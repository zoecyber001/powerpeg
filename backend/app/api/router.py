from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.rooms import router as rooms_router
from app.api.bookings import router as bookings_router
from app.api.devices import router as devices_router
from app.api.telemetry import router as telemetry_router
from app.api.alerts import router as alerts_router
from app.api.audit import router as audit_router
from app.services.websocket_manager import ws_manager
from app.services.seed_service import seed_data

api_router = APIRouter()

api_router.include_router(rooms_router)
api_router.include_router(bookings_router)
api_router.include_router(devices_router)
api_router.include_router(telemetry_router)
api_router.include_router(alerts_router)
api_router.include_router(audit_router)

@api_router.post("/demo/reset")
async def reset_demo_endpoint():
    await seed_data()
    await ws_manager.broadcast("DEMO_RESET", {"message": "Demo state reset to clean seed baseline"})
    return {"status": "success", "message": "Demo reset complete"}

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open, client can send ping or commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
