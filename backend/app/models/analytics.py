import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, JSON, Integer, Boolean, DateTime, Uuid, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class AnalyticsEvent(BaseModel):
    __tablename__ = "analytics_events"

    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    event_source: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    user = relationship("User", backref="analytics_events")


class AnalyticsMetric(BaseModel):
    __tablename__ = "analytics_metrics"

    metric_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ReportDefinition(BaseModel):
    __tablename__ = "report_definitions"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    creator = relationship("User", backref="report_definitions")


class ReportExecution(BaseModel):
    __tablename__ = "report_executions"

    report_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("report_definitions.id", ondelete="SET NULL"), nullable=True
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    executed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    definition = relationship("ReportDefinition", backref="executions")
    executor = relationship("User", backref="report_executions")


class DashboardSnapshot(BaseModel):
    __tablename__ = "dashboard_snapshots"

    snapshot_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    snapshot_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class KPIHistory(BaseModel):
    __tablename__ = "kpi_history"

    kpi_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    kpi_value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class AnalyticsAuditLog(BaseModel):
    __tablename__ = "analytics_audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    user = relationship("User", backref="analytics_audit_logs")
