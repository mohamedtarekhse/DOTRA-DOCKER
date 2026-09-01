from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ZoneBase(BaseModel):
    name: str
    zone_type: str
    is_restricted: bool = False
    min_lux_required: int = 100


class ZoneCreate(ZoneBase):
    pass


class ZoneOut(ZoneBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class CameraBase(BaseModel):
    name: str
    ip_address: str
    camera_type: str
    rtsp_url: str
    isapi_url: Optional[str] = None
    zone_id: Optional[UUID] = None
    config: dict = Field(default_factory=dict)


class CameraCreate(CameraBase):
    pass


class CameraOut(CameraBase):
    id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
