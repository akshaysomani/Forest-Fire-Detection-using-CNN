from sqlalchemy.ext.asyncio import AsyncSession
from app.services.health_service import health_service
from app.services.system_metrics import system_metrics
from app.repositories.dashboard_repository import dashboard_repository


class MonitoringService:
    async def get_system_summary(self, db: AsyncSession) -> dict:
        """
        Gathers live system health and performance statistics.
        Verifies DB connectivity, disk space capacity, active user sessions,
        and CPU/RAM loads.
        """
        db_healthy = await health_service.check_database_health(db)
        storage_healthy = health_service.check_storage_health()

        # Overall server state
        api_status = "healthy"
        if not db_healthy or not storage_healthy:
            api_status = "degraded"

        # Gather resource telemetry
        storage_usage = system_metrics.get_storage_usage()
        cpu_usage = system_metrics.get_cpu_usage_percent()
        memory_usage = system_metrics.get_memory_usage()

        # Database counts
        active_sess_count = await dashboard_repository.get_active_sessions_count(db)

        return {
            "api_status": api_status,
            "database_status": "healthy" if db_healthy else "unhealthy",
            "storage_usage": storage_usage,
            "cpu_usage_percent": cpu_usage,
            "memory_usage": memory_usage,
            "active_sessions": active_sess_count,
            "background_jobs_status": "healthy",
            "queue_status": "healthy",
        }


monitoring_service = MonitoringService()
