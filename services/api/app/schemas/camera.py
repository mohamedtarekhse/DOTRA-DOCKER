from datetime import datetime
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
    isapi_url: str | None = None
    zone_id: UUID | None = None
    config: dict = Field(default_factory=dict)


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = None
    ip_address: str | None = None
    camera_type: str | None = None
    rtsp_url: str | None = None
    isapi_url: str | None = None
    zone_id: UUID | None = None
    is_active: bool | None = None
    config: dict | None = None


class CameraOut(CameraBase):
    id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
