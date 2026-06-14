import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.alert import Alert
    from app.models.user import User
from sqlalchemy import String, ForeignKey, JSON, Integer, Boolean, DateTime, Uuid, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Location(BaseModel):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    elevation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Indexes are mapped to speed up bounding-box searches
    # Relationships
    incidents: Mapped[List["IncidentLocation"]] = relationship("IncidentLocation", back_populates="location", cascade="all, delete-orphan")
    alerts: Mapped[List["AlertLocation"]] = relationship("AlertLocation", back_populates="location", cascade="all, delete-orphan")


class Region(BaseModel):
    __tablename__ = "regions"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # Country, State, Forest Division, Forest Range
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    boundary: Mapped[dict] = mapped_column(JSON, nullable=False)  # GeoJSON coordinates dictionary

    # Relationships
    parent: Mapped[Optional["Region"]] = relationship("Region", remote_side="Region.id", backref="children")
    zones: Mapped[List["Zone"]] = relationship("Zone", back_populates="region", cascade="all, delete-orphan")


class Zone(BaseModel):
    __tablename__ = "zones"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    region_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("regions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # Monitoring Zone, Protected Area, Wildfire Buffer
    boundary: Mapped[dict] = mapped_column(JSON, nullable=False)  # GeoJSON polygon coordinates
    risk_level: Mapped[str] = mapped_column(String(20), default="Low", nullable=False)  # Low, Medium, High, Extreme

    # Relationships
    region: Mapped[Region] = relationship("Region", back_populates="zones")


class Geofence(BaseModel):
    __tablename__ = "geofences"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # Circular, Polygon
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)  # center/radius or list of points
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class IncidentLocation(BaseModel):
    __tablename__ = "incident_locations"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", backref="location_links")
    location: Mapped[Location] = relationship("Location", back_populates="incidents")


class AlertLocation(BaseModel):
    __tablename__ = "alert_locations"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relationships
    alert: Mapped["Alert"] = relationship("Alert", backref="location_links")
    location: Mapped[Location] = relationship("Location", back_populates="alerts")


class LocationHistory(BaseModel):
    __tablename__ = "location_history"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # responder, vehicle, drone
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)


class GISAuditLog(BaseModel):
    __tablename__ = "gis_audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", backref="gis_audit_logs")
