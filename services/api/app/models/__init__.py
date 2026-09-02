import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    JSON, String, Uuid, Text,
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from ..database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    zone_type = Column(String(50), nullable=False)
    is_restricted = Column(Boolean, default=False)
    min_lux_required = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    cameras = relationship("Camera", back_populates="zone")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(Uuid(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL"))
    name = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)
    camera_type = Column(String(50), nullable=False)
    rtsp_url = Column(Text, nullable=False)
    isapi_url = Column(Text)
    is_active = Column(Boolean, default=True)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    zone = relationship("Zone", back_populates="cameras")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate_number = Column(String(30), unique=True, nullable=False)
    owner_name = Column(String(150))
    owner_phone = Column(String(30))
    vehicle_type = Column(String(50))
    color = Column(String(30))
    department = Column(String(100))
    is_whitelisted = Column(Boolean, default=False)
    requires_exit_permission = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class WhitelistPermission(Base):
    __tablename__ = "whitelist_permissions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(Uuid(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"))
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    authorized_by = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)


class Person(Base):
    __tablename__ = "persons"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(50), unique=True)
    full_name = Column(String(150), nullable=False)
    department = Column(String(100))
    access_level = Column(String(50), default="standard")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(Uuid(as_uuid=True), ForeignKey("persons.id", ondelete="CASCADE"))
    embedding = Column(Vector(512), nullable=False)  # InsightFace buffalo_l vector
    sample_image_url = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class VehicleEvent(Base):
    __tablename__ = "vehicle_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(Uuid(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"))
    camera_id = Column(Uuid(as_uuid=True), ForeignKey("cameras.id", ondelete="SET NULL"))
    plate_number = Column(String(30), nullable=False)
    event_type = Column(String(50), nullable=False)
    direction = Column(String(10), nullable=False)
    snapshot_url = Column(Text)
    confidence = Column(Float)
    approved_by = Column(String(100))
    event_time = Column(DateTime(timezone=True), default=utc_now)


class PersonEvent(Base):
    __tablename__ = "person_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(Uuid(as_uuid=True), ForeignKey("persons.id", ondelete="SET NULL"))
    camera_id = Column(Uuid(as_uuid=True), ForeignKey("cameras.id", ondelete="SET NULL"))
    event_type = Column(String(50), nullable=False)
    face_snapshot_url = Column(Text)
    confidence = Column(Float)
    event_time = Column(DateTime(timezone=True), default=utc_now)


class ImageStore(Base):
    __tablename__ = "image_store"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(Uuid(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"))
    image_url = Column(Text, nullable=False)
    captured_at = Column(DateTime(timezone=True), default=utc_now)
    metadata = Column(JSON, default=dict)


class ImageEmbedding(Base):
    __tablename__ = "image_embeddings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(Uuid(as_uuid=True), ForeignKey("image_store.id", ondelete="CASCADE"))
    clip_embedding = Column(Vector(512), nullable=False)  # OpenCLIP ViT-B/32 vector
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(Uuid(as_uuid=True), ForeignKey("zones.id"))
    camera_id = Column(Uuid(as_uuid=True), ForeignKey("cameras.id"))
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="high")
    description = Column(Text, nullable=False)
    snapshot_url = Column(Text)
    status = Column(String(30), default="new")
    resolved_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=utc_now)
    resolved_at = Column(DateTime(timezone=True))