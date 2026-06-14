import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.user import User
from sqlalchemy import String, ForeignKey, JSON, Integer, Boolean, DateTime, Uuid, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Incident(BaseModel):
    __tablename__ = "incidents"

    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="Open", nullable=False, index=True
    )  # Open, Acknowledged, Assigned, In Progress, Escalated, Resolved, Closed
    severity: Mapped[str] = mapped_column(
        String(20), default="Medium", nullable=False, index=True
    )  # Critical, High, Medium, Low, Informational
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    alert: Mapped[Optional["Alert"]] = relationship("Alert", backref="incidents")
    events: Mapped[List["IncidentEvent"]] = relationship(
        "IncidentEvent", back_populates="incident", cascade="all, delete-orphan"
    )
    assignments: Mapped[List["IncidentAssignment"]] = relationship(
        "IncidentAssignment", back_populates="incident", cascade="all, delete-orphan"
    )
    updates: Mapped[List["IncidentUpdate"]] = relationship(
        "IncidentUpdate", back_populates="incident", cascade="all, delete-orphan"
    )
    status_history: Mapped[List["IncidentStatusHistory"]] = relationship(
        "IncidentStatusHistory", back_populates="incident", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["IncidentAuditLog"]] = relationship(
        "IncidentAuditLog", back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentEvent(BaseModel):
    __tablename__ = "incident_events"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    incident: Mapped[Incident] = relationship("Incident", back_populates="events")


class ResponseTeam(BaseModel):
    __tablename__ = "response_teams"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Active", nullable=False, index=True)  # Active, Inactive, On Break
    current_incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    members: Mapped[List["ResponseMember"]] = relationship(
        "ResponseMember", back_populates="team", cascade="all, delete-orphan"
    )
    assignments: Mapped[List["IncidentAssignment"]] = relationship(
        "IncidentAssignment", back_populates="team", cascade="all, delete-orphan"
    )
    current_incident: Mapped[Optional[Incident]] = relationship("Incident", foreign_keys=[current_incident_id])


class ResponseMember(BaseModel):
    __tablename__ = "response_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("response_teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), default="Responder", nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    team: Mapped[ResponseTeam] = relationship("ResponseTeam", back_populates="members")
    user: Mapped["User"] = relationship("User", backref="response_member_links")


class IncidentAssignment(BaseModel):
    __tablename__ = "incident_assignments"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("response_teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="Pending", nullable=False, index=True
    )  # Pending, Accepted, Rejected, Completed

    # Relationships
    incident: Mapped[Incident] = relationship("Incident", back_populates="assignments")
    team: Mapped[ResponseTeam] = relationship("ResponseTeam", back_populates="assignments")
    assigner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_by])


class IncidentUpdate(BaseModel):
    __tablename__ = "incident_updates"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    media_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    incident: Mapped[Incident] = relationship("Incident", back_populates="updates")
    user: Mapped["User"] = relationship("User", backref="incident_updates")


class IncidentStatusHistory(BaseModel):
    __tablename__ = "incident_status_history"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    old_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    transition_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    incident: Mapped[Incident] = relationship("Incident", back_populates="status_history")
    user: Mapped[Optional["User"]] = relationship("User", backref="incident_status_histories")


class IncidentAuditLog(BaseModel):
    __tablename__ = "incident_audit_logs"

    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    incident: Mapped[Optional[Incident]] = relationship("Incident", back_populates="audit_logs")
    user: Mapped[Optional["User"]] = relationship("User", backref="incident_audit_logs")
