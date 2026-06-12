import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import String, ForeignKey, JSON, Uuid, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class DatasetCategory(BaseModel):
    __tablename__ = "dataset_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="category")


class DatasetLabel(BaseModel):
    __tablename__ = "dataset_labels"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Dataset(BaseModel):
    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("dataset_categories.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, processing, archived
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)  # Comma-separated tags

    # Relationships
    category: Mapped[DatasetCategory] = relationship("DatasetCategory", back_populates="datasets")
    owner: Mapped["User"] = relationship("User", backref="datasets")
    versions: Mapped[list["DatasetVersion"]] = relationship(
        "DatasetVersion",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )
    files: Mapped[list["DatasetFile"]] = relationship(
        "DatasetFile",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )
    uploads: Mapped[list["DatasetUploadHistory"]] = relationship(
        "DatasetUploadHistory",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["DatasetAuditLog"]] = relationship(
        "DatasetAuditLog",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )


class DatasetVersion(BaseModel):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version_str", name="uq_dataset_version"),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    version_str: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'v1.0.0'
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, archived, deprecated
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="versions")
    creator: Mapped["User"] = relationship("User", backref="created_versions")
    files: Mapped[list["DatasetFile"]] = relationship(
        "DatasetFile",
        back_populates="version"
    )


class DatasetFile(BaseModel):
    __tablename__ = "dataset_files"

    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    md5_hash: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    label_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("dataset_labels.id", ondelete="SET NULL"), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="files")
    version: Mapped[DatasetVersion | None] = relationship("DatasetVersion", back_populates="files")
    label: Mapped[DatasetLabel | None] = relationship("DatasetLabel", backref="files")


class DatasetUploadHistory(BaseModel):
    __tablename__ = "dataset_upload_history"

    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed
    upload_type: Mapped[str] = mapped_column(String(50), nullable=False)  # single, bulk, zip
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="uploads")
    user: Mapped["User"] = relationship("User", backref="uploads")


class DatasetAuditLog(BaseModel):
    __tablename__ = "dataset_audit_logs"

    dataset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)  # e.g., dataset.create, dataset.upload
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    dataset: Mapped[Dataset | None] = relationship("Dataset", back_populates="audit_logs")
    user: Mapped["User | None"] = relationship("User", backref="dataset_audit_logs")
