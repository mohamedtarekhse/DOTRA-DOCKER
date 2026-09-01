from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: UUID
    zone_id: Optional[UUID] = None
    camera_id: Optional[UUID] = None
    alert_type: str
    severity: str
    description: str
    snapshot_url: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    status: str
    resolved_by: Optional[str] = None
