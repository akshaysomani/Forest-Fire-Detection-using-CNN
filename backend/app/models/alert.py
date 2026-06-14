import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.detection import Detection
    from app.models.user import User
from sqlalchemy import String, ForeignKey, JSON, Integer, Boolean, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Alert(BaseModel):
    __tablename__ = "alerts"

    detection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("detections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(20), default="Medium", nullable=False, index=True
    )  # Critical, High, Medium, Low, Informational
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False, index=True
    )  # active, acknowledged, resolved, escalated
    message: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relationships
    detection: Mapped[Optional["Detection"]] = relationship("Detection", backref="alerts")
    events: Mapped[List["AlertEvent"]] = relationship("AlertEvent", back_populates="alert", cascade="all, delete-orphan")
    notifications: Mapped[List["AlertNotification"]] = relationship(
        "AlertNotification", back_populates="alert", cascade="all, delete-orphan"
    )
    recipients: Mapped[List["AlertRecipient"]] = relationship(
        "AlertRecipient", back_populates="alert", cascade="all, delete-orphan"
    )
    acknowledgements: Mapped[List["AlertAcknowledgement"]] = relationship(
        "AlertAcknowledgement", back_populates="alert", cascade="all, delete-orphan"
    )


class AlertEvent(BaseModel):
    __tablename__ = "alert_events"

    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., fire_prediction, satellite_prediction, manual_alert
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    alert: Mapped[Optional[Alert]] = relationship("Alert", back_populates="events")


class AlertNotification(BaseModel):
    __tablename__ = "alert_notifications"

    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # email, in_app, sms, whatsapp
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)  # pending, sent, failed
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    alert: Mapped[Optional[Alert]] = relationship("Alert", back_populates="notifications")
    recipient: Mapped["User"] = relationship("User", backref="alert_notifications")


class AlertRecipient(BaseModel):
    __tablename__ = "alert_recipients"

    alert_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    alert: Mapped[Alert] = relationship("Alert", back_populates="recipients")
    user: Mapped["User"] = relationship("User", backref="alert_recipient_links")


class AlertPreference(BaseModel):
    __tablename__ = "alert_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # email, in_app, sms, whatsapp
    min_severity: Mapped[str] = mapped_column(String(20), default="Medium", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM format
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM format

    # Relationships
    user: Mapped["User"] = relationship("User", backref="alert_preferences")


class AlertAcknowledgement(BaseModel):
    __tablename__ = "alert_acknowledgements"

    alert_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # acknowledge, resolve
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relationships
    alert: Mapped[Alert] = relationship("Alert", back_populates="acknowledgements")
    user: Mapped["User"] = relationship("User", backref="alert_acknowledgements")


class AlertAuditLog(BaseModel):
    __tablename__ = "alert_audit_logs"

    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., alert_generated, alert_acknowledged, preference_updated
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    alert: Mapped[Optional[Alert]] = relationship("Alert", backref="audit_logs")
    user: Mapped[Optional["User"]] = relationship("User", backref="alert_audit_logs")
