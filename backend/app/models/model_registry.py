import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, ForeignKey, JSON, Integer, Boolean, DateTime, Uuid, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class RegisteredModel(BaseModel):
    __tablename__ = "models"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    creator = relationship("User", backref="registered_models")
    versions: Mapped[List["ModelVersion"]] = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")


class ModelVersion(BaseModel):
    __tablename__ = "model_versions"

    model_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    training_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("training_runs.id", ondelete="SET NULL"), nullable=True
    )
    checkpoint_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("training_checkpoints.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="Draft", nullable=False, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    release_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    hyperparameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    model: Mapped[RegisteredModel] = relationship("RegisteredModel", back_populates="versions")
    training_run = relationship("TrainingRun", backref="model_versions")
    checkpoint = relationship("TrainingCheckpoint", backref="model_versions")
    creator = relationship("User", backref="created_model_versions")

    artifacts: Mapped[List["ModelArtifact"]] = relationship(
        "ModelArtifact", back_populates="model_version", cascade="all, delete-orphan"
    )
    metadata_items: Mapped[List["ModelMetadata"]] = relationship(
        "ModelMetadata", back_populates="model_version", cascade="all, delete-orphan"
    )
    deployments: Mapped[List["ModelDeployment"]] = relationship(
        "ModelDeployment", back_populates="model_version", cascade="all, delete-orphan"
    )
    approvals: Mapped[List["ModelApproval"]] = relationship(
        "ModelApproval", back_populates="model_version", cascade="all, delete-orphan"
    )
    lifecycle_events: Mapped[List["ModelLifecycleEvent"]] = relationship(
        "ModelLifecycleEvent", back_populates="model_version", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["ModelAuditLog"]] = relationship(
        "ModelAuditLog", back_populates="model_version", cascade="all, delete-orphan"
    )


class ModelArtifact(BaseModel):
    __tablename__ = "model_artifacts"

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    uri: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="artifacts")
    creator = relationship("User", backref="uploaded_artifacts")


class ModelMetadata(BaseModel):
    __tablename__ = "model_metadata"

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), default="string", nullable=False)

    # Relationships
    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="metadata_items")


class ModelDeployment(BaseModel):
    __tablename__ = "model_deployments"

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    environment: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)
    deployed_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    undeployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="deployments")
    deployer = relationship("User", backref="model_deployments")


class ModelApproval(BaseModel):
    __tablename__ = "model_approvals"

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    request_notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    target_stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relationships
    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="approvals")
    requester = relationship("User", foreign_keys=[requested_by], backref="requested_approvals")
    reviewer = relationship("User", foreign_keys=[reviewed_by], backref="reviewed_approvals")


class ModelLifecycleEvent(BaseModel):
    __tablename__ = "model_lifecycle_events"

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_state: Mapped[str] = mapped_column(String(50), nullable=False)
    to_state: Mapped[str] = mapped_column(String(50), nullable=False)
    triggered_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    model_version: Mapped[ModelVersion] = relationship("ModelVersion", back_populates="lifecycle_events")
    trigger = relationship("User", backref="lifecycle_events")


class ModelAuditLog(BaseModel):
    __tablename__ = "model_audit_logs"

    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    performed_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    model_version: Mapped[Optional[ModelVersion]] = relationship("ModelVersion", back_populates="audit_logs")
    operator = relationship("User", backref="model_audit_logs")
