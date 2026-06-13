import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ModelCreateRequest(BaseModel):
    name: str = Field(..., max_length=100, description="Unique name of the model")
    description: Optional[str] = Field(None, max_length=500, description="Description of the model family")


class ModelResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelVersionCreateRequest(BaseModel):
    model_id: uuid.UUID
    training_run_id: Optional[uuid.UUID] = None
    checkpoint_id: Optional[uuid.UUID] = None
    description: Optional[str] = Field(None, max_length=1000)
    release_notes: Optional[str] = None


class ModelVersionResponse(BaseModel):
    id: uuid.UUID
    model_id: uuid.UUID
    version: str
    training_run_id: Optional[uuid.UUID] = None
    checkpoint_id: Optional[uuid.UUID] = None
    status: str
    created_by: Optional[uuid.UUID] = None
    description: Optional[str] = None
    release_notes: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelArtifactResponse(BaseModel):
    id: uuid.UUID
    model_version_id: uuid.UUID
    name: str
    artifact_type: str
    uri: str
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelMetadataResponse(BaseModel):
    id: uuid.UUID
    model_version_id: uuid.UUID
    key: str
    value: str
    value_type: str

    model_config = ConfigDict(from_attributes=True)


class ModelDeploymentResponse(BaseModel):
    id: uuid.UUID
    model_version_id: uuid.UUID
    environment: str
    status: str
    deployed_by: Optional[uuid.UUID] = None
    deployed_at: datetime
    undeployed_at: Optional[datetime] = None
    metrics: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ModelApprovalResponse(BaseModel):
    id: uuid.UUID
    model_version_id: uuid.UUID
    requested_by: uuid.UUID
    requested_at: datetime
    request_notes: Optional[str] = None
    target_stage: str
    status: str
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ModelLifecycleEventResponse(BaseModel):
    id: uuid.UUID
    model_version_id: uuid.UUID
    from_state: str
    to_state: str
    triggered_by: uuid.UUID
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelAuditLogResponse(BaseModel):
    id: uuid.UUID
    model_version_id: Optional[uuid.UUID] = None
    action: str
    performed_by: uuid.UUID
    details: Optional[Dict[str, Any]] = None
    client_ip: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelVersionDetailResponse(ModelVersionResponse):
    artifacts: List[ModelArtifactResponse] = []
    metadata_items: List[ModelMetadataResponse] = []
    deployments: List[ModelDeploymentResponse] = []
    approvals: List[ModelApprovalResponse] = []
    lifecycle_events: List[ModelLifecycleEventResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ApprovalRequestCreate(BaseModel):
    model_version_id: uuid.UUID
    target_stage: str = Field("Approved", description="Stage: Approved, Staging, Production")
    request_notes: Optional[str] = Field(None, max_length=500)


class ApprovalReviewRequest(BaseModel):
    approval_id: uuid.UUID
    status: str = Field(..., description="Status: approved, rejected")
    review_notes: Optional[str] = Field(None, max_length=1000)


class ModelDeploymentRequest(BaseModel):
    model_version_id: uuid.UUID
    environment: str = Field("production", description="Environment: staging, production")
    metrics: Optional[Dict[str, Any]] = None


class ModelRollbackRequest(BaseModel):
    model_id: uuid.UUID
    environment: str = Field("production", description="Environment: staging, production")


class ModelVersionCompareResponse(BaseModel):
    version_a: ModelVersionResponse
    version_b: ModelVersionResponse
    metrics_diff: Dict[str, Any]
    hyperparameters_diff: Dict[str, Any]


class PaginatedModels(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[ModelResponse]


class PaginatedModelVersions(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[ModelVersionResponse]
