import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class KPISummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fire_detection_count: int
    detection_accuracy: float
    incident_resolution_time_min: float
    alert_response_time_min: float
    active_incidents: int
    user_activity_count: int
    dataset_growth_bytes: int
    model_performance_score: float


class TrendItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_bucket: str
    value: float


class TrendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kpi_name: str
    trends: List[TrendItem]


class ReportDefinitionCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: Optional[str] = None
    report_type: str
    parameters: Dict[str, Any] = {}
    schedule_cron: Optional[str] = None
    is_scheduled: bool = False


class ReportDefinitionResponse(ReportDefinitionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    created_at: datetime


class ReportExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_definition_id: Optional[uuid.UUID] = None
    report_type: str
    executed_by: Optional[uuid.UUID] = None
    status: str
    format: str
    parameters: Dict[str, Any] = {}
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    created_at: datetime


class ReportGenerateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_type: str
    format: str  # "PDF", "CSV", "XLSX", "JSON"
    parameters: Dict[str, Any] = {}


class ExecutiveDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kpis: KPISummaryResponse
    regional_risk_index: Dict[str, float]
    fire_hazard_level: str  # "Low", "Medium", "High", "Extreme"
    active_responders_ratio: float
