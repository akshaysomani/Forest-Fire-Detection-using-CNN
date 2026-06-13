"""
Log Collector - Intercepts Python logging records and persists them to the database.

Provides an async-compatible handler that batches log records for efficient
database writes via the LoggingService.
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.services.observability.structured_logger import get_correlation_id

logger = logging.getLogger("observability.log_collector")


class LogCollector:
    """
    Collects structured log entries in memory for batch persistence.
    Designed to be flushed periodically or at request boundaries.
    """

    def __init__(self, max_buffer_size: int = 100):
        self._buffer: List[Dict[str, Any]] = []
        self._max_buffer_size = max_buffer_size

    def collect(
        self,
        level: str,
        message: str,
        logger_name: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a log entry to the in-memory buffer."""
        entry = {
            "timestamp": datetime.now(timezone.utc),
            "level": level.upper(),
            "message": message,
            "logger": logger_name,
            "correlation_id": correlation_id or get_correlation_id(),
            "metadata_json": metadata,
        }
        self._buffer.append(entry)

        if len(self._buffer) >= self._max_buffer_size:
            logger.debug(
                f"Log collector buffer reached {self._max_buffer_size}, "
                "consider flushing to database."
            )

    async def flush(self, db) -> int:
        """
        Persist all buffered log entries to the database via LoggingService.
        Returns the number of entries flushed.
        """
        if not self._buffer:
            return 0

        from app.services.observability.logging_service import logging_service

        entries_to_flush = self._buffer[:]
        self._buffer.clear()

        count = 0
        for entry in entries_to_flush:
            try:
                await logging_service.save_log(
                    db=db,
                    level=entry["level"],
                    message=entry["message"],
                    logger_name=entry["logger"],
                    correlation_id=entry["correlation_id"],
                    metadata_json=entry["metadata_json"],
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to flush log entry: {e}")

        await db.commit()
        return count

    @property
    def buffer_size(self) -> int:
        """Return the current number of buffered entries."""
        return len(self._buffer)

    def clear(self) -> None:
        """Discard all buffered entries."""
        self._buffer.clear()


# Module-level singleton
log_collector = LogCollector()
