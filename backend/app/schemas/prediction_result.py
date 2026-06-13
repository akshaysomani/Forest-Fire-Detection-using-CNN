import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class ProbabilityScore(BaseModel):
    non_fire: float = Field(..., alias="non-fire")
    fire: float = Field(..., alias="fire")

    model_config = ConfigDict(populate_by_name=True)


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    image_path: str
    filename: str
    prediction_label: str
    confidence: float
    model_name: str
    model_version: str
    is_verified_fire: Optional[bool] = None
    alert_sent: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class SinglePredictionResult(BaseModel):
    detection: PredictionResponse
    risk_level: str
    probabilities: ProbabilityScore
    processing_duration_seconds: float


class PaginatedPredictions(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[PredictionResponse]


class PredictionStatisticsResponse(BaseModel):
    total_predictions: int
    fire_count: int
    non_fire_count: int
    average_confidence: float
    average_latency_seconds: float
    accuracy_percentage: Optional[float] = None  # Percentage of verified predictions that were correct
