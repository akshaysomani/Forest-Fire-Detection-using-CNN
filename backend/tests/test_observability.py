"""
Comprehensive test suite for the Observability, Monitoring & Platform Reliability
Engineering System (Module 13).

Tests cover:
- Correlation ID propagation in context handlers
- Structured logger JSON formatting
- Log collection, storage, retrieval, and retention pruning
- In-memory metrics registry (counters/gauges)
- Metrics service flush and query
- APM throughput and latency distribution
- Distributed tracing span lifecycle
- Trace collector buffer and database flush
- SLI target evaluation and error budget calculation
- SLO compliance evaluation and recording
- Dependency health checking
- Platform health manager consolidation
- Dashboard adapter visualization formatting
- Reliability alert service SLO violation detection
- Availability tracker uptime calculation
- All /observability controller API endpoints with RBAC
"""
import pytest
import uuid
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.role import Role
from app.models.observability import (
    ObservabilityLog,
    MetricEntry,
    TraceSpan,
    SloCompliance,
    PerformanceMetric,
)
from app.services.password_service import password_service
from app.services.observability.structured_logger import (
    generate_correlation_id,
    set_correlation_id,
    get_correlation_id,
    correlation_id_var,
    StructuredJsonFormatter,
)
from app.services.observability.trace_manager import (
    generate_trace_id,
    generate_span_id,
    set_trace_id,
    get_trace_id,
    push_span,
    pop_span,
    get_current_span_id,
    get_parent_span_id,
    reset_trace_context,
)
from app.services.observability.metrics_registry import MetricsRegistry
from app.services.observability.log_collector import LogCollector
from app.services.observability.logging_service import logging_service
from app.services.observability.metrics_service import metrics_service
from app.services.observability.distributed_tracer import distributed_tracer
from app.services.observability.trace_collector import TraceCollector
from app.services.observability.sli_manager import SLIManager
from app.services.observability.slo_service import slo_service
from app.services.observability.reliability_alert_service import ReliabilityAlertService
from app.services.observability.availability_tracker import AvailabilityTracker
from app.services.observability.dependency_checker import dependency_checker
from app.services.observability.platform_health_manager import platform_health_manager
from app.services.observability.dashboard_adapter import dashboard_adapter
from app.services.observability.performance_monitor import performance_monitor

pytestmark = pytest.mark.asyncio


# ─── Test Helpers ─────────────────────────────────────────────────────────────


async def get_auth_headers(client: AsyncClient, username: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "Password123!"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_user_with_role(db: AsyncSession, username: str, role_name: str) -> User:
    query = select(Role).where(Role.name == role_name)
    res = await db.execute(query)
    role = res.scalar_one()

    user = User(
        email=f"{username}@forestfire.org",
        username=username,
        hashed_password=password_service.hash_password("Password123!"),
        is_active=True,
        is_verified=True,
    )
    user.roles.append(role)
    db.add(user)
    await db.flush()
    return user


# ─── Unit Tests: Structured Logger ───────────────────────────────────────────


async def test_correlation_id_context_propagation():
    """Test that correlation IDs are correctly set and retrieved from context."""
    cid = generate_correlation_id()
    assert cid is not None
    assert len(cid) == 36  # UUID format

    set_correlation_id(cid)
    assert get_correlation_id() == cid

    # Reset
    set_correlation_id(None)
    assert get_correlation_id() is None


async def test_structured_json_formatter():
    """Test that StructuredJsonFormatter produces valid JSON."""
    import json
    import logging

    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Test message"
    assert "timestamp" in parsed


# ─── Unit Tests: Trace Manager ───────────────────────────────────────────────


async def test_trace_context_management():
    """Test trace ID and span stack context propagation."""
    reset_trace_context()

    tid = generate_trace_id()
    set_trace_id(tid)
    assert get_trace_id() == tid

    # Push spans and verify hierarchy
    span1 = generate_span_id()
    push_span(span1)
    assert get_current_span_id() == span1
    assert get_parent_span_id() is None

    span2 = generate_span_id()
    push_span(span2)
    assert get_current_span_id() == span2
    assert get_parent_span_id() == span1

    # Pop and verify
    popped = pop_span()
    assert popped == span2
    assert get_current_span_id() == span1

    pop_span()
    assert get_current_span_id() is None

    reset_trace_context()


# ─── Unit Tests: Metrics Registry ────────────────────────────────────────────


async def test_metrics_registry_counters():
    """Test in-memory counter increment and retrieval."""
    registry = MetricsRegistry()

    registry.increment("test.counter", 1.0)
    assert registry.get_counter("test.counter") == 1.0

    registry.increment("test.counter", 5.0)
    assert registry.get_counter("test.counter") == 6.0

    registry.reset_all()
    assert registry.get_counter("test.counter") == 0.0


async def test_metrics_registry_gauges():
    """Test in-memory gauge set and retrieval."""
    registry = MetricsRegistry()

    registry.set_gauge("test.gauge", 42.5)
    assert registry.get_gauge("test.gauge") == 42.5

    registry.set_gauge("test.gauge", 99.9)
    assert registry.get_gauge("test.gauge") == 99.9

    registry.reset_all()


async def test_metrics_registry_snapshot():
    """Test snapshot generation for database flushing."""
    registry = MetricsRegistry()

    registry.increment("api.requests", 10)
    registry.set_gauge("system.cpu", 45.2)

    snapshot = registry.get_snapshot()
    assert len(snapshot) == 2

    names = [s["name"] for s in snapshot]
    assert "api.requests" in names
    assert "system.cpu" in names

    registry.reset_all()


# ─── Unit Tests: Log Collector ───────────────────────────────────────────────


async def test_log_collector_buffering():
    """Test log collector in-memory buffering."""
    collector = LogCollector(max_buffer_size=50)

    collector.collect("INFO", "Test message", "test_logger")
    assert collector.buffer_size == 1

    collector.collect("WARNING", "Warning message", "test_logger")
    assert collector.buffer_size == 2

    collector.clear()
    assert collector.buffer_size == 0


# ─── Integration Tests: Logging Service ──────────────────────────────────────


async def test_logging_service_save_and_query(db: AsyncSession):
    """Test saving and querying log entries."""
    await logging_service.save_log(
        db=db,
        level="INFO",
        message="Test log entry for query",
        logger_name="test_logger",
        correlation_id="test-correlation-123",
    )
    await db.commit()

    result = await logging_service.query_logs(db=db, level="INFO", limit=10)
    assert result["total"] >= 1

    items = result["items"]
    assert any(log.message == "Test log entry for query" for log in items)


async def test_logging_service_correlation_filter(db: AsyncSession):
    """Test filtering logs by correlation ID."""
    cid = "unique-corr-id-abc"
    await logging_service.save_log(
        db=db, level="ERROR", message="Correlated error", logger_name="test", correlation_id=cid
    )
    await db.commit()

    result = await logging_service.query_logs(db=db, correlation_id=cid)
    assert result["total"] >= 1
    assert all(log.correlation_id == cid for log in result["items"])


async def test_logging_service_statistics(db: AsyncSession):
    """Test log statistics aggregation."""
    await logging_service.save_log(db=db, level="INFO", message="Info msg", logger_name="test")
    await logging_service.save_log(db=db, level="ERROR", message="Error msg", logger_name="test")
    await db.commit()

    stats = await logging_service.get_log_statistics(db)
    assert stats["total_logs"] >= 2
    assert "info" in stats["level_distribution"]
    assert "error" in stats["level_distribution"]


async def test_logging_service_prune(db: AsyncSession):
    """Test log retention pruning."""
    # Create a log with old timestamp
    old_log = ObservabilityLog(
        timestamp=datetime.now(timezone.utc) - timedelta(days=60),
        level="DEBUG",
        message="Old log entry",
        logger="test",
    )
    db.add(old_log)
    await db.commit()

    pruned = await logging_service.prune_logs(db=db, retention_days=30)
    await db.commit()
    assert pruned >= 1


# ─── Integration Tests: Metrics Service ──────────────────────────────────────


async def test_metrics_service_record_and_query(db: AsyncSession):
    """Test recording and querying individual metrics."""
    await metrics_service.record_metric(
        db=db, name="test.metric", value=42.0, labels={"env": "test"}
    )
    await db.commit()

    result = await metrics_service.query_metrics(db=db, name="test.metric")
    assert result["total"] >= 1
    assert result["items"][0].value == 42.0


async def test_metrics_service_summary(db: AsyncSession):
    """Test metric statistical summary."""
    for val in [10.0, 20.0, 30.0, 40.0, 50.0]:
        await metrics_service.record_metric(db=db, name="test.summary", value=val)
    await db.commit()

    summary = await metrics_service.get_metric_summary(db=db, name="test.summary")
    assert summary["count"] == 5
    assert summary["min_value"] == 10.0
    assert summary["max_value"] == 50.0
    assert summary["avg_value"] == 30.0


# ─── Integration Tests: Performance Monitor ──────────────────────────────────


async def test_performance_monitor_record(db: AsyncSession):
    """Test recording request performance samples."""
    metric = await performance_monitor.record_request(
        db=db,
        endpoint="/api/v1/health",
        method="GET",
        latency_ms=15.5,
        status_code=200,
        db_query_time_ms=3.2,
        cache_hit=True,
    )
    await db.commit()
    assert metric.endpoint == "/api/v1/health"
    assert metric.latency_ms == 15.5


async def test_performance_monitor_summary(db: AsyncSession):
    """Test endpoint performance summary generation."""
    for i in range(5):
        await performance_monitor.record_request(
            db=db,
            endpoint="/api/v1/predictions",
            method="POST",
            latency_ms=100.0 + i * 10,
            status_code=200 if i < 4 else 500,
        )
    await db.commit()

    summaries = await performance_monitor.get_endpoint_summary(db)
    assert len(summaries) >= 1
    pred_summary = next(
        (s for s in summaries if s["endpoint"] == "/api/v1/predictions"), None
    )
    assert pred_summary is not None
    assert pred_summary["total_requests"] == 5


# ─── Integration Tests: Distributed Tracing ──────────────────────────────────


async def test_distributed_tracer_span_lifecycle():
    """Test span start/end lifecycle with timing."""
    reset_trace_context()
    set_trace_id("test-trace-001")

    span = distributed_tracer.start_span(name="test_operation")
    assert span.trace_id == "test-trace-001"
    assert span.name == "test_operation"

    # Simulate work
    time.sleep(0.01)

    span_data = distributed_tracer.end_span(span)
    assert span_data["status"] == "success"
    assert span_data["duration_ms"] > 0

    reset_trace_context()


async def test_trace_collector_flush(db: AsyncSession):
    """Test trace collector buffer and database flush."""
    collector = TraceCollector()

    reset_trace_context()
    set_trace_id("flush-test-trace")

    span = distributed_tracer.start_span(name="flush_test")
    span_data = distributed_tracer.end_span(span)
    collector.collect(span_data)

    assert collector.buffer_size == 1

    count = await collector.flush(db)
    await db.commit()
    assert count == 1
    assert collector.buffer_size == 0

    # Verify in database
    spans = await collector.query_traces(db, trace_id="flush-test-trace")
    assert len(spans) >= 1
    assert spans[0].name == "flush_test"

    reset_trace_context()


# ─── Unit Tests: SLI Manager ─────────────────────────────────────────────────


async def test_sli_manager_targets():
    """Test SLI target definitions and retrieval."""
    manager = SLIManager()

    targets = manager.get_all_targets()
    assert "api_availability" in targets
    assert "api_latency_p95" in targets
    assert "error_rate" in targets

    api_target = manager.get_target("api_availability")
    assert api_target["target_percentage"] == 99.5


async def test_sli_manager_compliance_evaluation():
    """Test SLI compliance evaluation with error budget calculation."""
    manager = SLIManager()

    # Compliant case
    result = manager.evaluate_compliance("api_availability", 99.8)
    assert result["compliant"] is True
    assert result["error_budget_remaining"] > 0

    # Non-compliant case
    result = manager.evaluate_compliance("api_availability", 98.0)
    assert result["compliant"] is False


# ─── Integration Tests: SLO Service ──────────────────────────────────────────


async def test_slo_evaluate_all(db: AsyncSession):
    """Test comprehensive SLO evaluation."""
    # Seed some performance data
    for i in range(10):
        await performance_monitor.record_request(
            db=db,
            endpoint="/api/v1/test",
            method="GET",
            latency_ms=50.0 + i,
            status_code=200,
        )
    await db.commit()

    result = await slo_service.evaluate_all_slos(db)
    assert "evaluations" in result
    assert "overall_compliant" in result
    assert "error_budgets" in result


async def test_slo_record_compliance(db: AsyncSession):
    """Test persisting SLO compliance records."""
    record = await slo_service.record_compliance(
        db=db,
        slo_name="api_availability",
        target_percentage=99.5,
        actual_percentage=99.8,
        window_days=30,
        compliant=True,
    )
    await db.commit()
    assert record.slo_name == "api_availability"
    assert record.compliant is True


async def test_slo_compliance_history(db: AsyncSession):
    """Test SLO compliance history retrieval."""
    await slo_service.record_compliance(
        db=db, slo_name="api_availability",
        target_percentage=99.5, actual_percentage=99.8,
        window_days=30, compliant=True,
    )
    await db.commit()

    history = await slo_service.get_compliance_history(db, slo_name="api_availability")
    assert len(history) >= 1
    assert history[0].slo_name == "api_availability"


# ─── Unit Tests: Reliability Alert Service ───────────────────────────────────


async def test_reliability_alert_compliant():
    """Test that no alert is triggered for compliant SLOs."""
    service = ReliabilityAlertService()
    alert = service.evaluate_and_alert({"compliant": True, "sli_name": "test"})
    assert alert is None


async def test_reliability_alert_violation():
    """Test that alerts are triggered for SLO violations."""
    service = ReliabilityAlertService()
    alert = service.evaluate_and_alert({
        "compliant": False,
        "sli_name": "api_availability",
        "target_percentage": 99.5,
        "actual_percentage": 97.0,
        "error_budget_remaining": 0.0,
    })
    assert alert is not None
    assert alert["alert_type"] == "slo_violation"
    assert alert["severity"] == "critical"


# ─── Unit Tests: Availability Tracker ────────────────────────────────────────


async def test_availability_tracker_recording():
    """Test availability ping recording and percentage calculation."""
    tracker = AvailabilityTracker()

    for _ in range(9):
        tracker.record_ping(success=True)
    tracker.record_ping(success=False)

    pct = tracker.get_availability_percentage(window_minutes=60)
    assert pct == 90.0


async def test_availability_tracker_uptime_summary():
    """Test uptime summary across multiple windows."""
    tracker = AvailabilityTracker()

    for _ in range(10):
        tracker.record_ping(success=True)

    summary = tracker.get_uptime_summary()
    assert summary["last_5_min"] == 100.0
    assert summary["total_pings"] == 10


# ─── Integration Tests: Dependency Checker ───────────────────────────────────


async def test_dependency_checker_database(db: AsyncSession):
    """Test database dependency health check."""
    result = await dependency_checker.check_database(db)
    assert result["status"] == "healthy"
    assert result["latency_ms"] >= 0


async def test_dependency_checker_storage():
    """Test storage dependency health check."""
    result = dependency_checker.check_storage()
    assert result["status"] in ("healthy", "degraded", "unhealthy")


async def test_dependency_checker_ml_models():
    """Test ML model dependency health check."""
    result = dependency_checker.check_ml_models(model_dir="storage")
    assert result["status"] in ("healthy", "degraded", "unhealthy")


async def test_dependency_checker_all(db: AsyncSession):
    """Test running all dependency checks."""
    results = await dependency_checker.check_all(db)
    assert "database" in results
    assert "storage" in results
    assert "ml_models" in results
    assert "queues" in results


# ─── Integration Tests: Platform Health Manager ──────────────────────────────


async def test_platform_health_report(db: AsyncSession):
    """Test comprehensive platform health report generation."""
    health = await platform_health_manager.get_platform_health(db)

    assert "status" in health
    assert health["status"] in ("healthy", "degraded", "unhealthy")
    assert "database" in health
    assert "storage" in health
    assert "system_metrics" in health
    assert "availability" in health


# ─── Unit Tests: Dashboard Adapter ───────────────────────────────────────────


async def test_dashboard_adapter_log_distribution():
    """Test log level distribution formatting."""
    stats = {
        "total_logs": 100,
        "level_distribution": {"info": 60, "warning": 25, "error": 10, "critical": 5},
    }
    chart = dashboard_adapter.format_log_distribution(stats)
    assert chart["chart_type"] == "distribution"
    assert len(chart["labels"]) == 4


async def test_dashboard_adapter_slo_compliance():
    """Test SLO compliance visualization formatting."""
    slo_results = {
        "evaluations": {
            "api_availability": {
                "target_percentage": 99.5,
                "actual_percentage": 99.8,
                "compliant": True,
                "error_budget_remaining": 0.3,
            },
        },
        "overall_compliant": True,
    }
    chart = dashboard_adapter.format_slo_compliance(slo_results)
    assert chart["chart_type"] == "gauge"
    assert len(chart["indicators"]) == 1
    assert chart["overall_compliant"] is True


# ─── API Controller Tests ────────────────────────────────────────────────────


async def test_observability_endpoints_require_auth(client: AsyncClient):
    """Test that all observability endpoints require authentication."""
    endpoints = [
        "/api/v1/observability/metrics",
        "/api/v1/observability/logs",
        "/api/v1/observability/traces",
        "/api/v1/observability/health",
        "/api/v1/observability/slo",
        "/api/v1/observability/reliability",
        "/api/v1/observability/performance",
    ]
    for ep in endpoints:
        response = await client.get(ep)
        assert response.status_code == 401, f"Endpoint {ep} should require auth"


async def test_observability_api_with_admin(client: AsyncClient, db: AsyncSession):
    """Test that admin users can access all observability endpoints."""
    admin = await create_user_with_role(db, "obs_admin", "Super Admin")
    await db.commit()

    headers = await get_auth_headers(client, "obs_admin")

    # Metrics endpoint
    resp = await client.get("/api/v1/observability/metrics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "live" in data
    assert "historical" in data

    # Logs endpoint
    resp = await client.get("/api/v1/observability/logs", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data

    # Traces endpoint
    resp = await client.get("/api/v1/observability/traces", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "recent_traces" in data

    # Health endpoint
    resp = await client.get("/api/v1/observability/health", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "database" in data

    # SLO endpoint
    resp = await client.get("/api/v1/observability/slo", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "current" in data
    assert "targets" in data

    # Reliability endpoint
    resp = await client.get("/api/v1/observability/reliability", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "dashboard_type" in data

    # Performance endpoint
    resp = await client.get("/api/v1/observability/performance", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "apm" in data
    assert "endpoint_summaries" in data


async def test_observability_logs_filtering(client: AsyncClient, db: AsyncSession):
    """Test log query filtering via API."""
    admin = await create_user_with_role(db, "obs_log_admin", "Super Admin")

    # Insert test log data
    await logging_service.save_log(
        db=db, level="ERROR", message="API filter test error",
        logger_name="filter_test", correlation_id="filter-corr-id",
    )
    await db.commit()

    headers = await get_auth_headers(client, "obs_log_admin")

    # Filter by level
    resp = await client.get(
        "/api/v1/observability/logs?level=ERROR", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["level"] == "ERROR" for item in data["items"])

    # Filter by correlation ID
    resp = await client.get(
        "/api/v1/observability/logs?correlation_id=filter-corr-id", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


async def test_observability_traces_by_id(client: AsyncClient, db: AsyncSession):
    """Test trace retrieval by specific trace ID."""
    admin = await create_user_with_role(db, "obs_trace_admin", "Super Admin")

    # Insert a trace span directly
    span = TraceSpan(
        trace_id="api-test-trace-001",
        span_id="span-001",
        name="test_api_span",
        service_name="forest-fire-detection",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        duration_ms=25.0,
        status="success",
    )
    db.add(span)
    await db.commit()

    headers = await get_auth_headers(client, "obs_trace_admin")
    resp = await client.get(
        "/api/v1/observability/traces?trace_id=api-test-trace-001", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == "api-test-trace-001"
    assert len(data["spans"]) >= 1


async def test_correlation_id_header_propagation(client: AsyncClient, db: AsyncSession):
    """Test that X-Correlation-ID is returned in response headers."""
    admin = await create_user_with_role(db, "obs_header_admin", "Super Admin")
    await db.commit()

    headers = await get_auth_headers(client, "obs_header_admin")
    resp = await client.get("/api/v1/observability/health", headers=headers)

    assert resp.status_code == 200
    assert "x-correlation-id" in resp.headers
    assert "x-trace-id" in resp.headers
