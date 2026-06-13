import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Log Schemas ---
class LogResponse(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    level: str
    message: str
    logger: str
    correlation_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class LogQueryResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[LogResponse]


# --- Metric Schemas ---
class MetricSample(BaseModel):
    id: uuid.UUID
    name: str
    value: float
    timestamp: datetime
    labels_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class MetricQueryResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[MetricSample]


# --- Trace / Span Schemas ---
class SpanDetail(BaseModel):
    id: uuid.UUID
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    service_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status: str
    error_message: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class TraceResponse(BaseModel):
    trace_id: str
    spans: List[SpanDetail]


# --- SLO / SLI Schemas ---
class SloDetails(BaseModel):
    id: uuid.UUID
    slo_name: str
    target_percentage: float
    actual_percentage: float
    window_days: int
    compliant: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class SloComplianceResponse(BaseModel):
    total: int
    items: List[SloDetails]
    overall_compliance: float
    error_budgets: Dict[str, float]  # Name -> Remaining budget %


# --- APM Performance Schemas ---
class PerformanceSample(BaseModel):
    id: uuid.UUID
    endpoint: str
    method: str
    latency_ms: float
    status_code: int
    db_query_time_ms: float
    cache_hit: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class PerformanceSummary(BaseModel):
    endpoint: str
    method: str
    avg_latency_ms: float
    p95_latency_ms: float
    error_rate: float
    throughput_rpm: float
    avg_db_query_time_ms: float
    cache_hit_rate: float
    total_requests: int


class PerformanceResponse(BaseModel):
    total: int
    items: List[PerformanceSample]
    summaries: List[PerformanceSummary]


# --- Health & Diagnostics Schemas ---
class DependencyHealth(BaseModel):
    status: str  # healthy, degraded, unhealthy
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class PlatformHealthReport(BaseModel):
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    api_status: str
    database: DependencyHealth
    storage: DependencyHealth
    ml_models: DependencyHealth
    queues: DependencyHealth
    system_metrics: Dict[str, Any]  # CPU, memory, storage loads
