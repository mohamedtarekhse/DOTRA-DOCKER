from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: UUID
    zone_id: UUID | None = None
    camera_id: UUID | None = None
    alert_type: str
    severity: str
    description: str
    snapshot_url: str | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    status: str
    resolved_by: str | None = None
