"""
Observability Controller - FastAPI routes for the Observability, Monitoring
& Platform Reliability Engineering System.

Exposes REST endpoints for metrics, logs, traces, health, SLO compliance,
reliability dashboards, and performance monitoring.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, PermissionChecker
from app.models.user import User

from app.services.observability.logging_service import logging_service
from app.services.observability.metrics_service import metrics_service
from app.services.observability.metrics_collector import metrics_collector
from app.services.observability.trace_collector import trace_collector
from app.services.observability.apm_service import apm_service
from app.services.observability.performance_monitor import performance_monitor
from app.services.observability.slo_service import slo_service
from app.services.observability.platform_health_manager import platform_health_manager
from app.services.observability.observability_dashboard_manager import observability_dashboard_manager
from app.services.observability.reliability_alert_service import reliability_alert_service
from app.services.observability.availability_tracker import availability_tracker
from app.services.observability.sli_manager import sli_manager

router = APIRouter()


# ─── Metrics Endpoints ───────────────────────────────────────────────────────


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_metrics(
    name: Optional[str] = Query(None, description="Filter by metric name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Retrieve system and application metrics with optional filtering.
    Requires 'view_reports' permission.
    """
    # Also collect live infrastructure metrics
    live_metrics = metrics_collector.collect_all()

    # Query persisted metrics from database
    db_metrics = await metrics_service.query_metrics(db=db, name=name, skip=skip, limit=limit)

    return {
        "live": live_metrics,
        "historical": {
            "total": db_metrics["total"],
            "skip": db_metrics["skip"],
            "limit": db_metrics["limit"],
            "items": [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    "labels_json": m.labels_json,
                }
                for m in db_metrics["items"]
            ],
        },
    }


# ─── Logs Endpoints ──────────────────────────────────────────────────────────


@router.get("/logs", status_code=status.HTTP_200_OK)
async def get_logs(
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARNING, ERROR, etc.)"),
    logger_name: Optional[str] = Query(None, description="Filter by logger name"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    search: Optional[str] = Query(None, description="Search in log messages"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Query structured log entries with filtering and pagination.
    Requires 'view_reports' permission.
    """
    result = await logging_service.query_logs(
        db=db,
        level=level,
        logger_name=logger_name,
        correlation_id=correlation_id,
        search=search,
        skip=skip,
        limit=limit,
    )

    return {
        "total": result["total"],
        "skip": result["skip"],
        "limit": result["limit"],
        "items": [
            {
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level,
                "message": log.message,
                "logger": log.logger,
                "correlation_id": log.correlation_id,
                "metadata_json": log.metadata_json,
            }
            for log in result["items"]
        ],
    }


# ─── Traces Endpoints ────────────────────────────────────────────────────────


@router.get("/traces", status_code=status.HTTP_200_OK)
async def get_traces(
    trace_id: Optional[str] = Query(None, description="Get spans for a specific trace ID"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Retrieve distributed trace data.
    If trace_id is provided, returns all spans for that trace.
    Otherwise, returns a summary of recent traces.
    Requires 'view_reports' permission.
    """
    if trace_id:
        spans = await trace_collector.query_traces(db=db, trace_id=trace_id)
        return {
            "trace_id": trace_id,
            "spans": [
                {
                    "id": str(s.id),
                    "trace_id": s.trace_id,
                    "span_id": s.span_id,
                    "parent_span_id": s.parent_span_id,
                    "name": s.name,
                    "service_name": s.service_name,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "duration_ms": s.duration_ms,
                    "status": s.status,
                    "error_message": s.error_message,
                    "metadata_json": s.metadata_json,
                }
                for s in spans
            ],
        }

    # Return recent trace summaries
    recent = await trace_collector.query_recent_traces(db=db, limit=limit)
    return {"recent_traces": recent}


# ─── Health Endpoints ─────────────────────────────────────────────────────────


@router.get("/health", status_code=status.HTTP_200_OK)
async def get_platform_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Get comprehensive platform health report including dependency statuses,
    system metrics, and availability data.
    Requires 'view_reports' permission.
    """
    return await platform_health_manager.get_platform_health(db)


# ─── SLO Endpoints ───────────────────────────────────────────────────────────


@router.get("/slo", status_code=status.HTTP_200_OK)
async def get_slo_compliance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Evaluate and return current SLO compliance status across all defined SLIs.
    Includes error budget calculations and compliance history.
    Requires 'view_reports' permission.
    """
    # Evaluate current SLOs
    slo_results = await slo_service.evaluate_all_slos(db)

    # Get SLI target definitions
    targets = sli_manager.get_all_targets()

    # Get compliance history
    history = await slo_service.get_compliance_history(db, limit=30)

    return {
        "current": slo_results,
        "targets": targets,
        "history": [
            {
                "id": str(h.id),
                "slo_name": h.slo_name,
                "target_percentage": h.target_percentage,
                "actual_percentage": h.actual_percentage,
                "window_days": h.window_days,
                "compliant": h.compliant,
                "timestamp": h.timestamp.isoformat() if h.timestamp else None,
            }
            for h in history
        ],
    }


# ─── Reliability Endpoints ───────────────────────────────────────────────────


@router.get("/reliability", status_code=status.HTTP_200_OK)
async def get_reliability_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Get the reliability engineering dashboard combining SLO compliance,
    availability tracking, error budgets, and reliability alerts.
    Requires 'view_reports' permission.
    """
    return await observability_dashboard_manager.get_reliability_dashboard(db)


# ─── Performance Endpoints ───────────────────────────────────────────────────


@router.get("/performance", status_code=status.HTTP_200_OK)
async def get_performance_analytics(
    endpoint: Optional[str] = Query(None, description="Filter by specific endpoint"),
    hours: int = Query(24, ge=1, le=720, description="Analysis window in hours"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Get APM performance analytics including throughput, latency distribution,
    error breakdown, and endpoint summaries.
    Requires 'view_reports' permission.
    """
    apm_summary = await apm_service.get_apm_summary(db, hours=hours)
    endpoint_summaries = await performance_monitor.get_endpoint_summary(db, endpoint=endpoint, hours=hours)

    return {
        "apm": apm_summary,
        "endpoint_summaries": endpoint_summaries,
    }
