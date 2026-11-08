import asyncio
import random
from typing import Dict, Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Room, Authorisation, Telemetry, utc_now
from app.database import AsyncSessionLocal
from app.services.anomaly_service import AnomalyService
from app.services.device_service import DeviceService
from app.services.websocket_manager import ws_manager
from app.config import settings

class SimulatorService:
    def __init__(self):
        self._room_states: Dict[int, Dict[str, Any]] = {}
        self._is_running = False
        self._bg_task: Optional[asyncio.Task] = None

    def get_or_init_room_state(self, room_id: int) -> Dict[str, Any]:
        if room_id not in self._room_states:
            self._room_states[room_id] = {
                "accumulated_kwh": round(random.uniform(12.0, 45.0), 3),
                "injection_mode": "NORMAL",
            }
        return self._room_states[room_id]

    def set_injection_mode(self, room_id: int, mode: str):
        state = self.get_or_init_room_state(room_id)
        state["injection_mode"] = mode

    def get_injection_mode(self, room_id: int) -> str:
        state = self.get_or_init_room_state(room_id)
        return state.get("injection_mode", "NORMAL")

    async def generate_step(self, db: AsyncSession, room: Room) -> Telemetry:
        state = self.get_or_init_room_state(room.id)
        mode = state["injection_mode"]

        auth_stmt = select(Authorisation).where(Authorisation.room_id == room.id).order_by(Authorisation.id.desc())
        auth_res = await db.execute(auth_stmt)
        auth = auth_res.scalar_one_or_none()
        is_authorised = auth.authorised if auth else False

        voltage = round(settings.NOMINAL_VOLTAGE_V + random.uniform(-2.5, 2.5), 1)

        if mode == "FORCE_ROGUE_DRAW":
            power = round(random.uniform(0.95, 1.45), 2)
        elif mode == "FORCE_ZERO":
            power = 0.0
        elif is_authorised:
            power = round(random.uniform(0.60, 1.35), 2)
        else:
            power = 0.0

        current = round((power * 1000.0) / voltage, 2) if voltage > 0 else 0.0
        hours = settings.TELEMETRY_INTERVAL_SECONDS / 3600.0
        state["accumulated_kwh"] = round(state["accumulated_kwh"] + (power * hours), 4)

        telemetry = Telemetry(
            room_id=room.id,
            source="SIMULATOR",
            voltage=voltage,
            current=current,
            power=power,
            energy=state["accumulated_kwh"],
            is_simulated=True,
            observed_at=utc_now()
        )
        db.add(telemetry)
        await db.flush()

        await AnomalyService.check_telemetry_anomalies(db, telemetry)

        await ws_manager.broadcast("TELEMETRY_UPDATED", {
            "room_id": room.id,
            "room_code": room.room_code,
            "voltage": telemetry.voltage,
            "current": telemetry.current,
            "power": telemetry.power,
            "energy": telemetry.energy,
            "is_simulated": True,
            "injection_mode": mode,
            "observed_at": telemetry.observed_at.isoformat()
        })

        return telemetry

    async def run_simulation_loop(self):
        while self._is_running:
            try:
                async with AsyncSessionLocal() as db:
                    await DeviceService.check_device_offline_timeouts(db)

                    stmt = select(Room)
                    res = await db.execute(stmt)
                    rooms = res.scalars().all()

                    for room in rooms:
                        await self.generate_step(db, room)

                    await db.commit()
            except Exception:
                pass

            await asyncio.sleep(settings.TELEMETRY_INTERVAL_SECONDS)

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._bg_task = asyncio.create_task(self.run_simulation_loop())

    def stop(self):
        self._is_running = False
        if self._bg_task:
            self._bg_task.cancel()

simulator_service = SimulatorService()
