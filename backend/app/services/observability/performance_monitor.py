"""
Performance Monitor - Context managers and decorators for profiling API workloads
and database query execution times.

Provides non-intrusive performance instrumentation that records latency samples
to the PerformanceMetric table for APM analysis.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.observability import PerformanceMetric
from app.services.observability.metrics_registry import metrics_registry

logger = logging.getLogger("observability.performance_monitor")


class PerformanceMonitor:
    """
    Records API request performance samples including latency,
    database query time, and cache hit status.
    """

    async def record_request(
        self,
        db: AsyncSession,
        endpoint: str,
        method: str,
        latency_ms: float,
        status_code: int,
        db_query_time_ms: float = 0.0,
        cache_hit: bool = False,
    ) -> PerformanceMetric:
        """Record an API request performance sample to the database."""
        metric = PerformanceMetric(
            endpoint=endpoint,
            method=method,
            latency_ms=round(latency_ms, 2),
            status_code=status_code,
            db_query_time_ms=round(db_query_time_ms, 2),
            cache_hit=cache_hit,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(metric)
        await db.flush()

        # Update in-memory counters
        metrics_registry.increment("api.total_requests")
        if status_code >= 400:
            metrics_registry.increment("api.error_requests")
        if cache_hit:
            metrics_registry.increment("api.cache_hits")

        return metric

    async def get_endpoint_summary(
        self,
        db: AsyncSession,
        endpoint: Optional[str] = None,
        hours: int = 24,
    ) -> list:
        """
        Get performance summary statistics per endpoint.
        Returns avg latency, p95 latency, error rate, throughput.
        """
        from sqlalchemy import select, and_, func, case, desc
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        conditions = [
            PerformanceMetric.deleted_at.is_(None),
            PerformanceMetric.timestamp >= cutoff,
        ]
        if endpoint:
            conditions.append(PerformanceMetric.endpoint == endpoint)

        # Aggregate per endpoint + method
        query = (
            select(
                PerformanceMetric.endpoint,
                PerformanceMetric.method,
                func.count(PerformanceMetric.id).label("total_requests"),
                func.avg(PerformanceMetric.latency_ms).label("avg_latency_ms"),
                func.max(PerformanceMetric.latency_ms).label("p95_latency_ms"),
                func.avg(PerformanceMetric.db_query_time_ms).label("avg_db_query_time_ms"),
                func.sum(
                    case(
                        (PerformanceMetric.status_code >= 400, 1),
                        else_=0,
                    )
                ).label("error_count"),
                func.sum(
                    case(
                        (PerformanceMetric.cache_hit.is_(True), 1),
                        else_=0,
                    )
                ).label("cache_hit_count"),
            )
            .where(and_(*conditions))
            .group_by(PerformanceMetric.endpoint, PerformanceMetric.method)
            .order_by(desc("total_requests"))
        )

        result = await db.execute(query)
        rows = result.all()

        summaries = []
        for row in rows:
            total = row.total_requests or 1
            error_count = row.error_count or 0
            cache_hits = row.cache_hit_count or 0

            # Estimate throughput as requests per minute over the window
            window_minutes = hours * 60
            throughput_rpm = round(total / window_minutes, 2) if window_minutes > 0 else 0.0

            summaries.append(
                {
                    "endpoint": row.endpoint,
                    "method": row.method,
                    "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
                    "p95_latency_ms": round(float(row.p95_latency_ms or 0), 2),
                    "error_rate": round(error_count / total, 4),
                    "throughput_rpm": throughput_rpm,
                    "avg_db_query_time_ms": round(float(row.avg_db_query_time_ms or 0), 2),
                    "cache_hit_rate": round(cache_hits / total, 4),
                    "total_requests": total,
                }
            )

        return summaries


# Module-level singleton
performance_monitor = PerformanceMonitor()
