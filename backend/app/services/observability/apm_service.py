"""
APM Service - Application Performance Monitoring engine.

Provides request throughput tracking, error rate calculation,
latency percentile analysis, and baseline distribution compilation
from persisted PerformanceMetric records.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.observability import PerformanceMetric
from app.services.observability.metrics_registry import metrics_registry

logger = logging.getLogger("observability.apm_service")


class APMService:
    """
    Application Performance Monitoring service.
    Computes real-time and historical performance analytics.
    """

    async def get_throughput(
        self,
        db: AsyncSession,
        hours: int = 1,
    ) -> Dict[str, Any]:
        """
        Calculate request throughput metrics over a specified window.
        Returns total requests, requests per minute, and error rate.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        conditions = [
            PerformanceMetric.deleted_at.is_(None),
            PerformanceMetric.timestamp >= cutoff,
        ]

        total_q = select(func.count(PerformanceMetric.id)).where(and_(*conditions))
        total_result = await db.execute(total_q)
        total = total_result.scalar() or 0

        error_q = select(func.count(PerformanceMetric.id)).where(
            and_(*conditions, PerformanceMetric.status_code >= 400)
        )
        error_result = await db.execute(error_q)
        errors = error_result.scalar() or 0

        window_minutes = max(hours * 60, 1)
        return {
            "total_requests": total,
            "requests_per_minute": round(total / window_minutes, 2),
            "error_count": errors,
            "error_rate": round(errors / max(total, 1), 4),
            "window_hours": hours,
        }

    async def get_latency_distribution(
        self,
        db: AsyncSession,
        endpoint: Optional[str] = None,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Compute latency distribution statistics.
        Returns min, max, avg, p50, p90, p95, p99 latency estimates.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        conditions = [
            PerformanceMetric.deleted_at.is_(None),
            PerformanceMetric.timestamp >= cutoff,
        ]
        if endpoint:
            conditions.append(PerformanceMetric.endpoint == endpoint)

        # Fetch all latency values for percentile calculation
        latency_q = (
            select(PerformanceMetric.latency_ms)
            .where(and_(*conditions))
            .order_by(PerformanceMetric.latency_ms)
        )
        result = await db.execute(latency_q)
        latencies = [row[0] for row in result.all()]

        if not latencies:
            return {
                "min_ms": 0.0,
                "max_ms": 0.0,
                "avg_ms": 0.0,
                "p50_ms": 0.0,
                "p90_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "sample_count": 0,
            }

        n = len(latencies)
        return {
            "min_ms": round(latencies[0], 2),
            "max_ms": round(latencies[-1], 2),
            "avg_ms": round(sum(latencies) / n, 2),
            "p50_ms": round(latencies[int(n * 0.50)], 2),
            "p90_ms": round(latencies[min(int(n * 0.90), n - 1)], 2),
            "p95_ms": round(latencies[min(int(n * 0.95), n - 1)], 2),
            "p99_ms": round(latencies[min(int(n * 0.99), n - 1)], 2),
            "sample_count": n,
        }

    async def get_error_breakdown(
        self,
        db: AsyncSession,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Break down errors by status code over a time window.
        Returns count per status code for 4xx and 5xx responses.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        conditions = [
            PerformanceMetric.deleted_at.is_(None),
            PerformanceMetric.timestamp >= cutoff,
            PerformanceMetric.status_code >= 400,
        ]

        query = (
            select(
                PerformanceMetric.status_code,
                func.count(PerformanceMetric.id).label("count"),
            )
            .where(and_(*conditions))
            .group_by(PerformanceMetric.status_code)
            .order_by(desc("count"))
        )

        result = await db.execute(query)
        return [
            {"status_code": row.status_code, "count": row.count}
            for row in result.all()
        ]

    async def get_apm_summary(
        self,
        db: AsyncSession,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Compile a full APM summary combining throughput, latency, and errors."""
        throughput = await self.get_throughput(db, hours=hours)
        latency = await self.get_latency_distribution(db, hours=hours)
        errors = await self.get_error_breakdown(db, hours=hours)

        return {
            "throughput": throughput,
            "latency_distribution": latency,
            "error_breakdown": errors,
            "window_hours": hours,
        }


# Module-level singleton
apm_service = APMService()
