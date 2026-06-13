"""
Metrics Service - Database-backed metric storage, retrieval, and aggregation.

Handles flushing in-memory registry snapshots to the database,
querying historical metric data, and computing statistical summaries.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.observability import MetricEntry
from app.services.observability.metrics_registry import metrics_registry

logger = logging.getLogger("observability.metrics_service")


class MetricsService:
    """Service for database-backed metric persistence and querying."""

    async def flush_registry(self, db: AsyncSession) -> int:
        """
        Flush all current in-memory registry snapshots to the database.
        Returns the count of metric entries persisted.
        """
        snapshot = metrics_registry.get_snapshot()
        count = 0

        for sample in snapshot:
            entry = MetricEntry(
                name=sample["name"],
                value=sample["value"],
                timestamp=sample["timestamp"],
                labels_json=sample.get("labels_json"),
            )
            db.add(entry)
            count += 1

        if count > 0:
            await db.flush()
            metrics_registry.reset_counters()
            logger.info(f"Flushed {count} metric entries to database")

        return count

    async def record_metric(
        self,
        db: AsyncSession,
        name: str,
        value: float,
        labels: Optional[Dict[str, Any]] = None,
    ) -> MetricEntry:
        """Record a single metric entry directly to the database."""
        entry = MetricEntry(
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc),
            labels_json=labels,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def query_metrics(
        self,
        db: AsyncSession,
        name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Query metric entries with optional filters and pagination."""
        conditions = [MetricEntry.deleted_at.is_(None)]

        if name:
            conditions.append(MetricEntry.name == name)
        if start_time:
            conditions.append(MetricEntry.timestamp >= start_time)
        if end_time:
            conditions.append(MetricEntry.timestamp <= end_time)

        # Count
        count_q = select(func.count(MetricEntry.id)).where(and_(*conditions))
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        # Data
        data_q = (
            select(MetricEntry)
            .where(and_(*conditions))
            .order_by(desc(MetricEntry.timestamp))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(data_q)
        items = list(result.scalars().all())

        return {"total": total, "skip": skip, "limit": limit, "items": items}

    async def get_metric_summary(
        self,
        db: AsyncSession,
        name: str,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Compute statistical summary for a named metric over a time window.
        Returns min, max, average, count, and latest value.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        conditions = [
            MetricEntry.deleted_at.is_(None),
            MetricEntry.name == name,
            MetricEntry.timestamp >= cutoff,
        ]

        stats_q = select(
            func.count(MetricEntry.id).label("count"),
            func.min(MetricEntry.value).label("min_value"),
            func.max(MetricEntry.value).label("max_value"),
            func.avg(MetricEntry.value).label("avg_value"),
        ).where(and_(*conditions))

        result = await db.execute(stats_q)
        row = result.one_or_none()

        # Latest value
        latest_q = (
            select(MetricEntry.value)
            .where(and_(*conditions))
            .order_by(desc(MetricEntry.timestamp))
            .limit(1)
        )
        latest_result = await db.execute(latest_q)
        latest = latest_result.scalar()

        return {
            "name": name,
            "window_hours": hours,
            "count": row.count if row else 0,
            "min_value": float(row.min_value) if row and row.min_value is not None else 0.0,
            "max_value": float(row.max_value) if row and row.max_value is not None else 0.0,
            "avg_value": round(float(row.avg_value), 4) if row and row.avg_value is not None else 0.0,
            "latest_value": float(latest) if latest is not None else 0.0,
        }


# Module-level singleton
metrics_service = MetricsService()
