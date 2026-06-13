import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.detection import Detection
from app.services.system_metrics import system_metrics
from app.repositories.dashboard_repository import dashboard_repository

logger = logging.getLogger("analytics.metrics_engine")


class MetricsEngine:
    async def get_system_telemetry(self, db: AsyncSession) -> dict:
        """Fetch real-time CPU, RAM, and Disk storage usage levels, and active sessions count."""
        cpu = system_metrics.get_cpu_usage_percent()
        ram = system_metrics.get_memory_usage()
        disk = system_metrics.get_storage_usage()
        active_sessions = await dashboard_repository.get_active_sessions_count(db)

        return {
            "cpu_usage_percent": cpu,
            "memory_usage": ram,
            "storage_usage": disk,
            "active_sessions": active_sessions
        }

    async def get_model_statistics(self, db: AsyncSession) -> list:
        """Fetch invocation counts and average confidence values per model."""
        return await dashboard_repository.get_model_usage_statistics(db)


metrics_engine = MetricsEngine()
