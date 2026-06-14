import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.alert_schema import AlertResponse


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    elevation: Optional[float] = None
    description: Optional[str] = None
    created_at: datetime


class LocationCreateRequest(BaseModel):
    name: str = Field(..., max_length=100)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    address: Optional[str] = Field(None, max_length=255)
    elevation: Optional[float] = Field(None)
    description: Optional[str] = Field(None, max_length=1000)


class RegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    type: str
    parent_id: Optional[uuid.UUID] = None
    boundary: Dict[str, Any]
    created_at: datetime


class RegionCreateRequest(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    type: str = Field(..., max_length=50, description="e.g. Country, State, Division, Range")
    parent_id: Optional[uuid.UUID] = Field(None)
    boundary: Dict[str, Any] = Field(..., description="GeoJSON coordinates dictionary")


class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    region_id: uuid.UUID
    type: str
    boundary: Dict[str, Any]
    risk_level: str
    created_at: datetime


class ZoneCreateRequest(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    region_id: uuid.UUID = Field(..., description="Parent region ID")
    type: str = Field(..., max_length=50, description="e.g. Monitoring Zone, Protected Area")
    boundary: Dict[str, Any] = Field(..., description="GeoJSON coordinates dictionary")
    risk_level: str = Field("Low", max_length=20, description="Risk level (Low, Medium, High, Extreme)")


class GeofenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    type: str
    geometry: Dict[str, Any]
    is_active: bool
    created_at: datetime


class GeofenceCreateRequest(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: str = Field(..., max_length=20, description="Circular or Polygon")
    geometry: Dict[str, Any] = Field(..., description="center/radius or points list")
    is_active: bool = Field(True)


class LocationHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    latitude: float
    longitude: float
    recorded_at: datetime
    created_at: datetime


class LocationHistoryCreateRequest(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: uuid.UUID = Field(..., description="Ranger user ID or drone ID")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class GISAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    details: Dict[str, Any]
    created_at: datetime


class AlertLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    location_id: uuid.UUID
    created_at: datetime
    location: LocationResponse
    alert: Optional[AlertResponse] = None


class IncidentLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    location_id: uuid.UUID
    created_at: datetime
    location: LocationResponse


class GISHistoryListResponse(BaseModel):
    items: List[LocationResponse]
    total_count: int


class GISRegionListResponse(BaseModel):
    items: List[RegionResponse]
    total_count: int


class GISZoneListResponse(BaseModel):
    items: List[ZoneResponse]
    total_count: int


class GISGeofenceListResponse(BaseModel):
    items: List[GeofenceResponse]
    total_count: int


class GISAuditHistoryResponse(BaseModel):
    logs: List[GISAuditLogResponse]
    total_count: int
