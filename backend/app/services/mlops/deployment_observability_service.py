import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.mlops.deployment_monitor import deployment_monitor
from app.services.mlops.deployment_metrics import deployment_metrics
from app.services.mlops.environment_registry import environment_registry

logger = logging.getLogger("mlops.deployment_observability_service")


class DeploymentObservabilityService:
    @staticmethod
    async def get_metrics_summary(db: AsyncSession) -> dict:
        """
        Compiles health indicators and execution stats for deployments,
        releases, and active environments.
        """
        total = await deployment_monitor.get_total_deployments_count(db)
        succeeded = await deployment_monitor.get_deployments_by_status_count(db, "succeeded")
        failed = await deployment_monitor.get_deployments_by_status_count(db, "failed")
        
        success_rate = 1.0
        if (succeeded + failed) > 0:
            success_rate = float(succeeded) / float(succeeded + failed)

        rollback_freq = await deployment_metrics.get_rollback_frequency(db)
        avg_duration = await deployment_monitor.get_average_duration_seconds(db)
        stability = await deployment_metrics.get_release_stability_index(db)

        # Retrieve environment status mapping
        envs, _ = await environment_registry.list_environments(db, 0, 100)
        env_health = {env.name: env.status for env in envs}

        return {
            "deployment_success_rate": success_rate,
            "total_deployments": total,
            "successful_deployments": succeeded,
            "failed_deployments": failed,
            "rollback_frequency": rollback_freq,
            "average_deployment_duration_seconds": avg_duration,
            "environment_health_statuses": env_health,
            "release_stability_index": stability
        }


deployment_observability_service = DeploymentObservabilityService()
