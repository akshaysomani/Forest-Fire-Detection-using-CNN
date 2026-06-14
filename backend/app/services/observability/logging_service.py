"""
Logging Service - Centralized log storage, retrieval, and retention management.

Provides database-backed log querying with filtering by level, logger name,
correlation ID, and time ranges. Supports retention pruning for compliance.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, desc, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.observability import ObservabilityLog

logger = logging.getLogger("observability.logging_service")


class LoggingService:
    """Service for storing, querying, and managing observability log entries."""

    async def save_log(
        self,
        db: AsyncSession,
        level: str,
        message: str,
        logger_name: str,
        correlation_id: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> ObservabilityLog:
        """Persist a structured log entry to the database."""
        log_entry = ObservabilityLog(
            timestamp=datetime.now(timezone.utc),
            level=level.upper(),
            message=message,
            logger=logger_name,
            correlation_id=correlation_id,
            metadata_json=metadata_json,
        )
        db.add(log_entry)
        await db.flush()
        return log_entry

    async def query_logs(
        self,
        db: AsyncSession,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Query logs with optional filters.
        Returns paginated results with total count.
        """
        conditions = [ObservabilityLog.deleted_at.is_(None)]

        if level:
            conditions.append(ObservabilityLog.level == level.upper())
        if logger_name:
            conditions.append(ObservabilityLog.logger == logger_name)
        if correlation_id:
            conditions.append(ObservabilityLog.correlation_id == correlation_id)
        if start_time:
            conditions.append(ObservabilityLog.timestamp >= start_time)
        if end_time:
            conditions.append(ObservabilityLog.timestamp <= end_time)
        if search:
            conditions.append(ObservabilityLog.message.ilike(f"%{search}%"))

        # Count query
        count_q = select(func.count(ObservabilityLog.id)).where(and_(*conditions))
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        # Data query
        data_q = (
            select(ObservabilityLog)
            .where(and_(*conditions))
            .order_by(desc(ObservabilityLog.timestamp))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(data_q)
        items = list(result.scalars().all())

        return {"total": total, "skip": skip, "limit": limit, "items": items}

    async def prune_logs(
        self,
        db: AsyncSession,
        retention_days: int = 30,
    ) -> int:
        """
        Soft-delete log entries older than the retention window.
        Returns the number of records pruned.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        query = select(ObservabilityLog).where(
            and_(
                ObservabilityLog.timestamp < cutoff,
                ObservabilityLog.deleted_at.is_(None),
            )
        )
        result = await db.execute(query)
        logs = result.scalars().all()
        count = 0
        for log in logs:
            log.deleted_at = datetime.now(timezone.utc)
            count += 1
        await db.flush()
        logger.info(f"Pruned {count} log entries older than {retention_days} days")
        return count

    async def get_log_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get aggregated log statistics by level."""
        conditions = [ObservabilityLog.deleted_at.is_(None)]

        total_q = select(func.count(ObservabilityLog.id)).where(and_(*conditions))
        total_result = await db.execute(total_q)
        total = total_result.scalar() or 0

        # Count per level
        level_counts = {}
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            level_q = select(func.count(ObservabilityLog.id)).where(and_(*conditions, ObservabilityLog.level == level))
            level_result = await db.execute(level_q)
            level_counts[level.lower()] = level_result.scalar() or 0

        return {
            "total_logs": total,
            "level_distribution": level_counts,
        }


logging_service = LoggingService()
