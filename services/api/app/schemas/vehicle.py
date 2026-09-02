from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class VehicleCreate(BaseModel):
    plate_number: str
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    vehicle_type: Optional[str] = None
    color: Optional[str] = None
    department: Optional[str] = None
    is_whitelisted: bool = True
    requires_exit_permission: bool = True


class VehicleUpdate(BaseModel):
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    vehicle_type: Optional[str] = None
    color: Optional[str] = None
    department: Optional[str] = None
    is_whitelisted: Optional[bool] = None
    requires_exit_permission: Optional[bool] = None


class VehicleOut(VehicleCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class VehicleEventIn(BaseModel):
    plate_number: str
    camera_id: Optional[UUID] = None
    direction: str
    confidence: Optional[float] = None
    snapshot_url: Optional[str] = None


class ExitApprovalIn(BaseModel):
    event_id: UUID
    approved: bool
    manager: str
