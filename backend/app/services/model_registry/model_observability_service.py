from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_registry.model_registry_monitor import model_registry_monitor
from app.services.model_registry.model_metrics import ModelRegistryMetrics


class ModelObservabilityService:
    @staticmethod
    async def get_metrics(db: AsyncSession) -> ModelRegistryMetrics:
        """Retrieves system observability telemetry for model registration, approvals, and deployments."""
        return await model_registry_monitor.collect_registry_metrics(db)


model_observability_service = ModelObservabilityService()
