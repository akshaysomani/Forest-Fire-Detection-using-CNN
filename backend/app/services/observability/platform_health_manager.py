"""
Platform Health Manager - Consolidates all health check results into a unified report.

Combines dependency health checks, system metrics, availability tracking,
and SLO compliance into a single platform health status.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.observability.dependency_checker import dependency_checker
from app.services.observability.availability_tracker import availability_tracker
from app.services.observability.metrics_collector import metrics_collector

logger = logging.getLogger("observability.platform_health_manager")


class PlatformHealthManager:
    """
    Consolidates all subsystem health statuses into a unified platform health report.
    Determines overall platform status based on dependency health states.
    """

    async def get_platform_health(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Generate a comprehensive platform health report.
        Returns overall status, dependency statuses, system metrics,
        and availability data.
        """
        # Run all dependency checks
        dependencies = await dependency_checker.check_all(db)

        # Collect infrastructure metrics
        infra_metrics = metrics_collector.collect_infrastructure_metrics()

        # Get availability summary
        uptime = availability_tracker.get_uptime_summary()

        # Determine overall platform status
        overall_status = self._compute_overall_status(dependencies)

        # Record availability ping based on dependencies
        all_healthy = all(
            dep.get("status") == "healthy"
            for dep in dependencies.values()
        )
        availability_tracker.record_ping(success=all_healthy)

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "api_status": "healthy" if all_healthy else "degraded",
            "database": dependencies["database"],
            "storage": dependencies["storage"],
            "ml_models": dependencies["ml_models"],
            "queues": dependencies["queues"],
            "system_metrics": {
                "cpu_usage_percent": infra_metrics.get("cpu_usage_percent", 0.0),
                "memory": infra_metrics.get("memory", {}),
                "storage": infra_metrics.get("storage", {}),
            },
            "availability": uptime,
        }

    def _compute_overall_status(self, dependencies: Dict[str, Dict[str, Any]]) -> str:
        """
        Determine overall platform status from individual dependency statuses.
        - 'healthy': All dependencies healthy
        - 'degraded': Any dependency degraded (but none unhealthy)
        - 'unhealthy': Any critical dependency (database) is unhealthy
        """
        statuses = [dep.get("status", "unknown") for dep in dependencies.values()]

        if "unhealthy" in statuses:
            # Check if a critical dependency (database) is unhealthy
            if dependencies.get("database", {}).get("status") == "unhealthy":
                return "unhealthy"
            return "degraded"

        if "degraded" in statuses:
            return "degraded"

        return "healthy"


# Module-level singleton
platform_health_manager = PlatformHealthManager()
