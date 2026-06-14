import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, JSON, Uuid, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Image(BaseModel):
    __tablename__ = "images"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    md5_hash: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    upload_source: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # dataset, manual, drone, cctv, satellite
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False, index=True
    )  # active, processing, archived, deleted

    # Relationships
    owner: Mapped["User"] = relationship("User", backref="uploaded_images")
    metadata_relation: Mapped["ImageMetadata | None"] = relationship(
        "ImageMetadata", back_populates="image", cascade="all, delete-orphan", uselist=False
    )
    versions: Mapped[list["ImageVersion"]] = relationship("ImageVersion", back_populates="image", cascade="all, delete-orphan")
    processing_logs: Mapped[list["ImageProcessingLog"]] = relationship(
        "ImageProcessingLog", back_populates="image", cascade="all, delete-orphan"
    )
    storage_locations: Mapped[list["ImageStorageLocation"]] = relationship(
        "ImageStorageLocation", back_populates="image", cascade="all, delete-orphan"
    )
    access_logs: Mapped[list["ImageAccessLog"]] = relationship(
        "ImageAccessLog", back_populates="image", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["ImageAuditLog"]] = relationship(
        "ImageAuditLog", back_populates="image", cascade="all, delete-orphan"
    )


class ImageMetadata(BaseModel):
    __tablename__ = "image_metadata"

    image_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("images.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    exif_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    gps_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    camera_make: Mapped[str | None] = mapped_column(String(100), nullable=True)
    camera_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    image: Mapped[Image] = relationship("Image", back_populates="metadata_relation")


class ImageVersion(BaseModel):
    __tablename__ = "image_versions"

    image_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 for original, 2, 3, etc.
    purpose: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # original, resized, normalized, thumbnail, augmented
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    md5_hash: Mapped[str] = mapped_column(String(32), nullable=False)

    # Relationships
    image: Mapped[Image] = relationship("Image", back_populates="versions")
    storage_locations: Mapped[list["ImageStorageLocation"]] = relationship(
        "ImageStorageLocation", back_populates="image_version", cascade="all, delete-orphan"
    )


class ImageProcessingLog(BaseModel):
    __tablename__ = "image_processing_logs"

    image_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # resize, normalize, thumbnail, augment
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)  # pending, success, failed
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    image: Mapped[Image] = relationship("Image", back_populates="processing_logs")


class ImageStorageLocation(BaseModel):
    __tablename__ = "image_storage_locations"

    image_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    image_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("image_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # local, s3, gcs, azure
    bucket_or_container: Mapped[str] = mapped_column(String(100), nullable=False)
    file_key_or_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    image: Mapped[Image] = relationship("Image", back_populates="storage_locations")
    image_version: Mapped[ImageVersion | None] = relationship("ImageVersion", back_populates="storage_locations")


class ImageAccessLog(BaseModel):
    __tablename__ = "image_access_logs"

    image_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    access_type: Mapped[str] = mapped_column(String(50), nullable=False)  # read, download, delete
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationships
    image: Mapped[Image] = relationship("Image", back_populates="access_logs")
    user: Mapped["User | None"] = relationship("User", backref="image_accesses")


class ImageAuditLog(BaseModel):
    __tablename__ = "image_audit_logs"

    image_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # create, update_metadata, archive, soft_delete, permanent_delete
    changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    image: Mapped[Image] = relationship("Image", back_populates="audit_logs")
    user: Mapped["User | None"] = relationship("User", backref="image_audits")
