import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Release Schemas ---
class ReleaseCreateRequest(BaseModel):
    version: str = Field(..., max_length=50, description="Release version number (e.g. v1.0.0)")
    description: Optional[str] = Field(None, max_length=1000)
    model_version_id: Optional[uuid.UUID] = None
    release_notes: Optional[str] = None


class ReleaseResponse(BaseModel):
    id: uuid.UUID
    version: str
    description: Optional[str] = None
    model_version_id: Optional[uuid.UUID] = None
    status: str
    created_by: uuid.UUID
    release_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Environment Schemas ---
class EnvironmentCreateRequest(BaseModel):
    name: str = Field(..., max_length=50, description="Environment name (e.g. staging)")
    description: Optional[str] = Field(None, max_length=500)
    config_schema: Optional[Dict[str, Any]] = None
    config_data: Optional[Dict[str, Any]] = None


class EnvironmentResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str
    current_release_id: Optional[uuid.UUID] = None
    config_schema: Optional[Dict[str, Any]] = None
    config_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Deployment Schemas ---
class DeploymentCreateRequest(BaseModel):
    environment_id: uuid.UUID
    model_version_id: uuid.UUID


class DeploymentPromoteRequest(BaseModel):
    deployment_job_id: uuid.UUID
    target_environment_id: uuid.UUID


class DeploymentRollbackRequest(BaseModel):
    environment_id: uuid.UUID


class DeploymentJobResponse(BaseModel):
    id: uuid.UUID
    environment_id: uuid.UUID
    model_version_id: uuid.UUID
    status: str
    steps: List[Dict[str, Any]]
    rollback_job_id: Optional[uuid.UUID] = None
    deployed_by: uuid.UUID
    duration_seconds: Optional[int] = None
    metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Observability Metrics Schemas ---
class DeploymentObservabilityResponse(BaseModel):
    deployment_success_rate: float
    total_deployments: int
    successful_deployments: int
    failed_deployments: int
    rollback_frequency: float
    average_deployment_duration_seconds: float
    environment_health_statuses: Dict[str, str]
    release_stability_index: float
