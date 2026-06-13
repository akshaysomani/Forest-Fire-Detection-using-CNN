import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ResponseMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    is_available: bool
    created_at: datetime


class ResponseTeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    specialty: str
    status: str
    current_incident_id: Optional[uuid.UUID] = None
    created_at: datetime


class ResponseTeamDetailsResponse(ResponseTeamResponse):
    members: List[ResponseMemberResponse] = []



class ResponseTeamCreateRequest(BaseModel):
    name: str = Field(..., max_length=100, description="Unique name of the response team")
    specialty: str = Field(..., max_length=100, description="Specialty description, e.g. Wildfire Suppression")


class ResponseMemberCreateRequest(BaseModel):
    user_id: uuid.UUID = Field(..., description="ID of the user to register as team responder")
    role: str = Field("Responder", max_length=50, description="Role of the responder (e.g. Commander, Responder)")


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    status: str
    severity: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class IncidentAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    team_id: uuid.UUID
    assigned_by: Optional[uuid.UUID] = None
    assigned_at: datetime
    status: str


class IncidentAssignmentCreateRequest(BaseModel):
    team_id: uuid.UUID = Field(..., description="Response team ID to assign")


class IncidentAssignmentRejectRequest(BaseModel):
    reason: str = Field(..., max_length=500, description="Reason for rejecting the assignment")


class IncidentUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    user_id: uuid.UUID
    message: str
    media_path: Optional[str] = None
    created_at: datetime


class IncidentUpdateCreateRequest(BaseModel):
    message: str = Field(..., max_length=1000, description="Situation update / sitrep content")
    media_path: Optional[str] = Field(None, max_length=512, description="Optional attachment file path")


class IncidentStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    old_status: str
    new_status: str
    transition_reason: Optional[str] = None
    created_at: datetime


class IncidentAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    action: str
    details: Dict[str, Any]
    created_at: datetime


class IncidentDetailsResponse(IncidentResponse):
    assignments: List[IncidentAssignmentResponse] = []
    updates: List[IncidentUpdateResponse] = []
    status_history: List[IncidentStatusHistoryResponse] = []


class IncidentHistoryResponse(BaseModel):
    incidents: List[IncidentResponse]
    total_count: int


class IncidentAuditHistoryResponse(BaseModel):
    logs: List[IncidentAuditLogResponse]
    total_count: int


class ManualIncidentCreateRequest(BaseModel):
    alert_id: Optional[uuid.UUID] = Field(None, description="Optional alert ID to link")
    title: str = Field(..., max_length=100, description="Descriptive title of the incident")
    description: Optional[str] = Field(None, max_length=1000, description="Additional incident details")
    severity: str = Field("Medium", description="Incident severity (Critical, High, Medium, Low, Informational)")
    latitude: Optional[float] = Field(None, description="Decimal latitude coordinates")
    longitude: Optional[float] = Field(None, description="Decimal longitude coordinates")
    transition_reason: Optional[str] = Field(None, description="Reason / note for manual creation")


class IncidentStatusTransitionRequest(BaseModel):
    status: str = Field(..., description="Target status: Open, Acknowledged, Assigned, In Progress, Escalated, Resolved, Closed")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for the status transition")


class IncidentEscalationRequest(BaseModel):
    reason: str = Field(..., max_length=500, description="Manual escalation reason details")
