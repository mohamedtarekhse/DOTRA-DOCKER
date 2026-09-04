from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PersonCreate(BaseModel):
    employee_id: str | None = None
    full_name: str
    department: str | None = None
    access_level: str = "standard"


class PersonOut(PersonCreate):
    id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FaceEnrollIn(BaseModel):
    person_id: UUID
    image_url: str


class FaceMatchIn(BaseModel):
    image_url: str
    threshold: float = 0.6
