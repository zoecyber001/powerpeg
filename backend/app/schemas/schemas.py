from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class RoomBase(BaseModel):
    room_code: str = Field(..., json_schema_extra={"example": "ROOM-204"})
    display_name: str = Field(..., json_schema_extra={"example": "Deluxe Suite 204"})
    status: str = Field("available", json_schema_extra={"example": "available"})

class RoomCreate(RoomBase):
    assigned_device_id: Optional[int] = None

class RoomUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[str] = None
    assigned_device_id: Optional[int] = None

class RoomResponse(RoomBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    assigned_device_id: Optional[int] = None

class DeviceBase(BaseModel):
    device_code: str = Field(..., json_schema_extra={"example": "AZ3166-01"})
    device_type: str = Field("AZ3166", json_schema_extra={"example": "AZ3166"})
    room_id: Optional[int] = None
    firmware_version: str = Field("1.0.0", json_schema_extra={"example": "1.0.0"})

class DeviceRegister(DeviceBase):
    pass

class DeviceHeartbeat(BaseModel):
    device_code: str
    reported_relay_state: str = Field(..., json_schema_extra={"example": "ON"})
    firmware_version: Optional[str] = "1.0.0"

class DeviceCommandAck(BaseModel):
    command_id: int
    status: str = Field("ACKNOWLEDGED", json_schema_extra={"example": "ACKNOWLEDGED"})
    reported_relay_state: str = Field(..., json_schema_extra={"example": "ON"})
    response_payload: Optional[str] = None

class DeviceCommandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    device_id: int
    command: str
    status: str
    issued_at: datetime
    acknowledged_at: Optional[datetime] = None
    response_payload: Optional[str] = None

class DeviceResponse(DeviceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    connection_status: str
    reported_relay_state: str
    last_seen_at: Optional[datetime] = None
    registered_at: datetime

class BookingCreate(BaseModel):
    room_id: int
    guest_label: str = Field(..., json_schema_extra={"example": "Alice Johnson"})
    start_at: datetime
    end_at: datetime
    booking_status: str = Field("confirmed", json_schema_extra={"example": "confirmed"})

class BookingUpdate(BaseModel):
    guest_label: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    booking_status: Optional[str] = None

class PaymentUpdate(BaseModel):
    payment_status: str = Field(..., json_schema_extra={"example": "confirmed"})
    amount: Optional[float] = 150.0

class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    booking_id: int
    payment_status: str
    amount: float
    is_simulated: bool = True
    updated_at: datetime
    updated_by: str

class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    guest_label: str
    start_at: datetime
    end_at: datetime
    booking_status: str
    created_by: str
    created_at: datetime
    payment: Optional[PaymentResponse] = None

class AuthorisationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    booking_id: Optional[int] = None
    authorised: bool
    reason: str
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    updated_at: datetime

class ManualOverrideRequest(BaseModel):
    room_id: int
    authorised: bool
    reason: str = Field(..., json_schema_extra={"example": "VIP early access approved by Manager"})
    duration_minutes: int = Field(60, json_schema_extra={"example": 60})

class TelemetryIngest(BaseModel):
    room_id: int
    source: str = "SIMULATOR"
    voltage: float = 230.0
    current: float
    power: float
    energy: float
    is_simulated: bool = True

class TelemetryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    source: str
    voltage: float
    current: float
    power: float
    energy: float
    is_simulated: bool = True
    observed_at: datetime

class AlertAcknowledge(BaseModel):
    acknowledged_by: str = Field(..., json_schema_extra={"example": "frontdesk_jane"})

class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    alert_type: str
    severity: str
    description: str
    status: str
    created_at: datetime
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_type: str
    actor_id: str
    event_type: str
    target_type: str
    target_id: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

class RoomDetailResponse(BaseModel):
    room: RoomResponse
    device: Optional[DeviceResponse] = None
    active_booking: Optional[BookingResponse] = None
    authorisation: Optional[AuthorisationResponse] = None
    latest_telemetry: Optional[TelemetryResponse] = None
    active_alerts: List[AlertResponse] = []
