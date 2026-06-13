import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SecurityEventResponse(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    event_type: str
    severity: str
    description: str
    user_id: Optional[uuid.UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class AccessReviewCampaignResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    target_role: Optional[str] = None
    created_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AccessReviewDecisionResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    reviewer_id: uuid.UUID
    decision: str
    decision_date: datetime
    justification: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AccessReviewDecisionCreate(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    decision: str = Field(..., pattern="^(CERTIFIED|REVOKED)$")
    justification: Optional[str] = None


class AccessReviewCampaignCreate(BaseModel):
    name: str
    target_role: Optional[str] = None


class SecretMetadataResponse(BaseModel):
    id: uuid.UUID
    key: str
    description: Optional[str] = None
    encryption_algorithm: str
    last_rotated_at: datetime
    next_rotation_due: datetime
    rotation_interval_days: int
    version: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class SecretRotationRequest(BaseModel):
    key: str


class CompliancePolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    category: str
    status: str
    last_checked_at: datetime
    details_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ComplianceAuditResponse(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    policy_name: str
    checked_by_id: Optional[uuid.UUID] = None
    status: str
    findings: Optional[str] = None
    details_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DataRetentionLogResponse(BaseModel):
    id: uuid.UUID
    execution_date: datetime
    table_name: str
    records_pruned: int
    status: str
    details_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ThreatIndicator(BaseModel):
    ip_address: str
    threat_type: str
    severity: str
    score: float
    first_seen: datetime
    last_seen: datetime
    request_count: int
    blocked: bool


class ThreatResponse(BaseModel):
    threats: List[ThreatIndicator]
    total_threats: int
    blocked_ips_count: int
    high_severity_count: int


class GovernanceDashboardResponse(BaseModel):
    overall_risk_score: float
    compliance_score: float  # e.g. 0.0 to 100.0
    active_threats_count: int
    pending_access_reviews_count: int
    last_secret_rotation: Optional[datetime] = None
    status_summary: Dict[str, Any]
