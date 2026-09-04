from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class VehicleCreate(BaseModel):
    plate_number: str
    owner_name: str | None = None
    owner_phone: str | None = None
    vehicle_type: str | None = None
    color: str | None = None
    department: str | None = None
    is_whitelisted: bool = True
    requires_exit_permission: bool = True


class VehicleUpdate(BaseModel):
    owner_name: str | None = None
    owner_phone: str | None = None
    vehicle_type: str | None = None
    color: str | None = None
    department: str | None = None
    is_whitelisted: bool | None = None
    requires_exit_permission: bool | None = None


class VehicleOut(VehicleCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class VehicleEventIn(BaseModel):
    plate_number: str
    camera_id: UUID | None = None
    direction: str
    confidence: float | None = None
    snapshot_url: str | None = None


class ExitApprovalIn(BaseModel):
    event_id: UUID
    approved: bool
    manager: str
