import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, JSON, Integer, Text, Uuid, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Release(BaseModel):
    __tablename__ = "releases"

    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    release_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    model_version = relationship("ModelVersion", backref="releases")
    creator = relationship("User", backref="created_releases")


class Environment(BaseModel):
    __tablename__ = "environments"

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="healthy", nullable=False)
    current_release_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("releases.id", ondelete="SET NULL"),
        nullable=True
    )
    config_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    config_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    current_release = relationship("Release", backref="active_environments")


class DeploymentJob(BaseModel):
    __tablename__ = "deployment_jobs"

    environment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("environments.id", ondelete="CASCADE"),
        nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    steps: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    rollback_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("deployment_jobs.id", ondelete="SET NULL"),
        nullable=True
    )
    deployed_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    environment = relationship("Environment", backref="deployment_jobs")
    model_version = relationship("ModelVersion", backref="deployment_jobs")
    deployer = relationship("User", backref="deployment_jobs")
