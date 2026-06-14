import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.prediction_result import PredictionResponse


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    detection_id: Optional[uuid.UUID] = None
    severity: str
    status: str
    message: str
    created_at: datetime
    updated_at: datetime
    detection: Optional[PredictionResponse] = None


class AlertEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: Optional[uuid.UUID] = None
    event_type: str
    payload: Dict[str, Any]
    created_at: datetime


class AlertNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: Optional[uuid.UUID] = None
    recipient_id: uuid.UUID
    channel: str
    status: str
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime


class AlertPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    channel: str
    min_severity: str
    enabled: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    created_at: datetime


class AlertPreferenceUpdate(BaseModel):
    channel: str = Field(..., description="Target notification channel (email, in_app, sms)")
    min_severity: Optional[str] = Field(
        None, description="Minimum severity level (Critical, High, Medium, Low, Informational)"
    )
    enabled: Optional[bool] = Field(None, description="Enable or disable notifications on this channel")
    quiet_hours_start: Optional[str] = Field(None, description="Quiet hours start time (HH:MM format)")
    quiet_hours_end: Optional[str] = Field(None, description="Quiet hours end time (HH:MM format)")


class AlertAcknowledgeRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000, description="Acknowledgement verification notes")


class AlertResolveRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000, description="Resolution verification notes")


class ManualAlertCreateRequest(BaseModel):
    severity: str = Field("Medium", description="Severity level: Critical, High, Medium, Low, Informational")
    message: str = Field(..., max_length=500, description="Alert message text")
    detection_id: Optional[uuid.UUID] = Field(None, description="Link optional detection event ID")
    payload: Optional[Dict[str, Any]] = Field(None, description="Additional context payload data")


class AlertAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    action: str
    details: Dict[str, Any]
    created_at: datetime


class AlertDetailsResponse(AlertResponse):
    events: List[AlertEventResponse] = []
    notifications: List[AlertNotificationResponse] = []


class AlertHistoryResponse(BaseModel):
    alerts: List[AlertResponse]
    total_count: int


class AlertAuditHistoryResponse(BaseModel):
    logs: List[AlertAuditLogResponse]
    total_count: int
