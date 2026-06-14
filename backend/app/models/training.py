import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.dataset import Dataset, DatasetVersion
    from app.models.user import User
from sqlalchemy import String, ForeignKey, JSON, Integer, Float, Boolean, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class TrainingRun(BaseModel):
    __tablename__ = "training_runs"

    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, running, completed, failed, stopped, resuming
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., custom_cnn, resnet18, mobilenet_v3
    hyperparameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics_history: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # List of epoch stats: [{"epoch": 1, "train_loss": 0.4, ...}]
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", backref="training_runs")
    dataset_version: Mapped[Optional["DatasetVersion"]] = relationship("DatasetVersion", backref="training_runs")
    user: Mapped["User"] = relationship("User", backref="training_runs")
    checkpoints: Mapped[List["TrainingCheckpoint"]] = relationship(
        "TrainingCheckpoint", back_populates="run", cascade="all, delete-orphan"
    )


class TrainingCheckpoint(BaseModel):
    __tablename__ = "training_checkpoints"

    run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False)
    epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    val_loss: Mapped[float] = mapped_column(Float, nullable=False)
    val_accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    checkpoint_path: Mapped[str] = mapped_column(String(512), nullable=False)  # Path in storage
    is_best: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    run: Mapped[TrainingRun] = relationship("TrainingRun", back_populates="checkpoints")
