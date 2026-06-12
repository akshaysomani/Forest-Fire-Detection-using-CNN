import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict


class TrainingStartRequest(BaseModel):
    dataset_id: uuid.UUID
    version_str: Optional[str] = None
    model_name: str  # e.g., custom_cnn, resnet18, mobilenet_v3, efficientnet_b0
    hyperparameters: Optional[Dict[str, Any]] = None


class TrainingRunResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: Optional[uuid.UUID] = None
    status: str
    model_name: str
    hyperparameters: Optional[Dict[str, Any]] = None
    metrics_history: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingCheckpointResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    epoch: int
    val_loss: float
    val_accuracy: float
    checkpoint_path: str
    is_best: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedTrainingRuns(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[TrainingRunResponse]
