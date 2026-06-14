import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, Boolean, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class Detection(BaseModel):
    __tablename__ = "detections"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    prediction_label: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'fire' or 'non-fire'
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="CNN_ResNet50_v1", nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    
    # Human Verification details for model accuracy calculations
    is_verified_fire: Mapped[bool | None] = mapped_column(Boolean, default=None, nullable=True, index=True)  
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Location metrics
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    user: Mapped["User | None"] = relationship("User", backref="detections")
