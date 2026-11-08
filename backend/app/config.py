import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "PegPower"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./powerpeg.db")
    DEVICE_HEARTBEAT_TIMEOUT_SECONDS: int = int(os.getenv("DEVICE_HEARTBEAT_TIMEOUT_SECONDS", "15"))
    TELEMETRY_INTERVAL_SECONDS: float = float(os.getenv("TELEMETRY_INTERVAL_SECONDS", "2.0"))
    UNAUTHORISED_ACTIVE_POWER_KW_THRESHOLD: float = 0.05
    NOMINAL_VOLTAGE_V: float = 230.0
    SECRET_KEY: str = os.getenv("SECRET_KEY", "pegpower-hackathon-supersecret-key-2026")

settings = Settings()
