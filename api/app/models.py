from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, 
    UniqueConstraint, Text, BigInteger, Enum as SQLEnum, Date, Numeric, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from geoalchemy2 import Geometry
import enum
import uuid as uuid_pkg

from .db import Base


class ScanStatus(str, enum.Enum):
    uploaded = "uploaded"
    ingested = "ingested"
    graded = "graded"
    error = "error"


class ScanQuality(str, enum.Enum):
    good = "good"
    medium = "medium"
    bad = "bad"


# ============ Auth & RBAC ============

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    farm_links = relationship("UserFarm", back_populates="user", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)

    user = relationship("User", back_populates="roles")
    role = relationship("Role")


# ============ User ↔ Farm Access ============

class UserFarm(Base):
    __tablename__ = "user_farms"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), primary_key=True)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="farm_links")
    farm = relationship("Farm", back_populates="user_links")


# ============ Farms & Animals ============

class Farm(Base):
    __tablename__ = "farms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    geofence = Column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=True)
    centroid = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_links = relationship("UserFarm", back_populates="farm", cascade="all, delete-orphan")
    geofences = relationship("FarmGeofence", back_populates="farm", cascade="all, delete-orphan")
    cattle = relationship("Cattle", back_populates="farm", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_farms_geofence_gist", geofence, postgresql_using="gist"),
    )


class FarmGeofence(Base):
    __tablename__ = "farm_geofences"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    geometry = Column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    farm = relationship("Farm", back_populates="geofences")

    __table_args__ = (
        Index("idx_farm_geofences_geom_gist", geometry, postgresql_using="gist"),
    )


class Cattle(Base):
    __tablename__ = "cattle"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    born_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farm = relationship("Farm", back_populates="cattle")
    scans = relationship("Scan", back_populates="cattle")
    animals = relationship("Animal", back_populates="cattle")


class Animal(Base):
    __tablename__ = "animals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=True)
    tag_id: Mapped[str] = mapped_column(Text, nullable=False)
    rfid: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    breed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    birth_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    cattle_id = Column(UUID(as_uuid=True), ForeignKey("cattle.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("farm_id", "tag_id", name="uq_farm_animal_tag"),
    )

    farm = relationship("Farm")
    cattle = relationship("Cattle", back_populates="animals")
    scans = relationship("Scan", back_populates="animal")


# ============ Devices ============

class Device(Base):
    __tablename__ = "devices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    device_code: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=True)
    s3_prefix_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_upload_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    captures_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farm = relationship("Farm")


# ============ Assets ============

class Asset(Base):
    __tablename__ = "assets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    bucket: Mapped[str] = mapped_column(Text, nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("bucket", "object_key", name="uq_asset_bucket_key"),
    )


# ============ Scans ============

class Scan(Base):
    __tablename__ = "scans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    scan_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    capture_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    ingest_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=True)
    animal_id = Column(UUID(as_uuid=True), ForeignKey("animals.id"), nullable=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    gps = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[ScanStatus] = mapped_column(SQLEnum(ScanStatus), default=ScanStatus.uploaded)
    image_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    mask_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    grading = Column(Text, nullable=True)
    meta = Column(JSONB, nullable=True)
    cattle_id = Column(UUID(as_uuid=True), ForeignKey("cattle.id", ondelete="SET NULL"), nullable=True)
    imf = Column(Numeric(6, 4), nullable=True)
    backfat_thickness = Column(Numeric(6, 3), nullable=True)
    animal_weight = Column(Numeric(10, 2), nullable=True)
    animal_rfid = Column(Text, nullable=True)
    ribeye_area = Column(Numeric(8, 2), nullable=True)
    clarity = Column(SQLEnum(ScanQuality, name="scan_clarity_enum"), nullable=True)
    usability = Column(SQLEnum(ScanQuality, name="scan_usability_enum"), nullable=True)
    label = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_scans_device_captured", "device_id", "captured_at"),
        Index("idx_scans_farm_captured", "farm_id", "captured_at"),
        Index("idx_scans_status_created", "status", "created_at"),
    )

    device = relationship("Device")
    farm = relationship("Farm")
    animal = relationship("Animal", back_populates="scans")
    operator = relationship("User")
    image_asset = relationship("Asset", foreign_keys=[image_asset_id])
    mask_asset = relationship("Asset", foreign_keys=[mask_asset_id])
    grading_results = relationship(
        "GradingResult",
        back_populates="scan",
        cascade="all, delete-orphan",
    )
    cattle = relationship("Cattle", back_populates="scans")


# ============ Scan Events ============

class ScanEvent(Base):
    __tablename__ = "scan_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    event: Mapped[str] = mapped_column(Text, nullable=False)
    meta = Column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_scan_events_scan_time", "scan_id", "created_at"),
    )

    scan = relationship("Scan")


# ============ Ingestion Log ============

class IngestionLog(Base):
    __tablename__ = "ingestion_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    capture_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    ingest_key: Mapped[str] = mapped_column(Text, nullable=False)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bytes_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_ingest_log_key_time", "ingest_key", "created_at"),
    )


# ============ Grading Results ============

class GradingResult(Base):
    __tablename__ = "grading_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    inference_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence = Column(Numeric(5, 4), nullable=True)
    confidence_breakdown = Column(JSONB, nullable=True)
    features_used = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_grading_scan_time", "scan_id", "created_at"),
        Index("idx_grading_model_ver", "model_name", "model_version"),
    )

    scan = relationship("Scan", back_populates="grading_results")
    creator = relationship("User")


# ============ Notifications ============

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    payload = Column(JSONB, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_notifications_user_time", "user_id", "created_at"),
    )

    user = relationship("User")
