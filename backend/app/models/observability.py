import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, JSON, Float, Integer, Text, Uuid, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel


class ObservabilityLog(BaseModel):
    __tablename__ = "observability_logs"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    logger: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class MetricEntry(BaseModel):
    __tablename__ = "metric_entries"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    labels_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class TraceSpan(BaseModel):
    __tablename__ = "trace_spans"

    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    span_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class SloCompliance(BaseModel):
    __tablename__ = "slo_compliance_records"

    slo_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    actual_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    compliant: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )


class PerformanceMetric(BaseModel):
    __tablename__ = "performance_metrics"

    endpoint: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    db_query_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
