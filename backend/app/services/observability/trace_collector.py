"""
Trace Collector - Batches completed trace span records for async database persistence.

Buffers finished spans in memory and provides a flush method to persist
them to the TraceSpan database table. Designed for efficient batch writes.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.observability import TraceSpan

logger = logging.getLogger("observability.trace_collector")


class TraceCollector:
    """
    In-memory buffer for completed trace spans.
    Flush periodically or at request boundaries.
    """

    def __init__(self, max_buffer_size: int = 200):
        self._buffer: List[Dict[str, Any]] = []
        self._max_buffer_size = max_buffer_size

    def collect(self, span_data: Dict[str, Any]) -> None:
        """Add a completed span record to the buffer."""
        self._buffer.append(span_data)

        if len(self._buffer) >= self._max_buffer_size:
            logger.debug(f"Trace collector buffer at {self._max_buffer_size}, consider flushing.")

    async def flush(self, db: AsyncSession) -> int:
        """
        Persist all buffered span records to the database.
        Returns the number of spans flushed.
        """
        if not self._buffer:
            return 0

        entries = self._buffer[:]
        self._buffer.clear()

        count = 0
        for span_data in entries:
            try:
                span_record = TraceSpan(
                    trace_id=span_data["trace_id"],
                    span_id=span_data["span_id"],
                    parent_span_id=span_data.get("parent_span_id"),
                    name=span_data["name"],
                    service_name=span_data.get("service_name", "forest-fire-detection"),
                    start_time=span_data["start_time"],
                    end_time=span_data["end_time"],
                    duration_ms=span_data["duration_ms"],
                    status=span_data.get("status", "success"),
                    error_message=span_data.get("error_message"),
                    metadata_json=span_data.get("metadata_json"),
                )
                db.add(span_record)
                count += 1
            except Exception as e:
                logger.error(f"Failed to persist trace span: {e}")

        if count > 0:
            await db.flush()
            logger.info(f"Flushed {count} trace spans to database")

        return count

    async def query_traces(
        self,
        db: AsyncSession,
        trace_id: str,
    ) -> List[TraceSpan]:
        """Retrieve all spans for a specific trace ID from the database."""
        from sqlalchemy import select, and_, asc

        query = (
            select(TraceSpan)
            .where(
                and_(
                    TraceSpan.trace_id == trace_id,
                    TraceSpan.deleted_at.is_(None),
                )
            )
            .order_by(asc(TraceSpan.start_time))
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def query_recent_traces(
        self,
        db: AsyncSession,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent unique trace IDs with their root span info.
        Returns a summary list of recent traces.
        """
        from sqlalchemy import select, and_, desc, func

        # Get distinct trace IDs ordered by most recent
        query = (
            select(
                TraceSpan.trace_id,
                func.min(TraceSpan.start_time).label("start_time"),
                func.count(TraceSpan.id).label("span_count"),
                func.sum(TraceSpan.duration_ms).label("total_duration_ms"),
            )
            .where(TraceSpan.deleted_at.is_(None))
            .group_by(TraceSpan.trace_id)
            .order_by(desc("start_time"))
            .limit(limit)
        )
        result = await db.execute(query)
        traces = []
        for row in result.all():
            traces.append(
                {
                    "trace_id": row.trace_id,
                    "start_time": row.start_time.isoformat() if row.start_time else None,
                    "span_count": row.span_count,
                    "total_duration_ms": round(float(row.total_duration_ms or 0), 2),
                }
            )
        return traces

    @property
    def buffer_size(self) -> int:
        """Return the current buffer size."""
        return len(self._buffer)

    def clear(self) -> None:
        """Discard all buffered spans."""
        self._buffer.clear()


# Module-level singleton
trace_collector = TraceCollector()
