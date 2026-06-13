import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mlops import DeploymentJob
from app.services.mlops.model_deployment_service import model_deployment_service
from app.services.mlops.deployment_orchestrator import deployment_orchestrator
from app.services.mlops.environment_registry import environment_registry
from app.core.exceptions import ValidationException, EntityNotFoundException

logger = logging.getLogger("mlops.promotion_manager")


class PromotionManager:
    @staticmethod
    async def promote_deployment(
        db: AsyncSession,
        deployment_job_id: uuid.UUID,
        target_environment_id: uuid.UUID,
        promoted_by: uuid.UUID
    ) -> DeploymentJob:
        """
        Promotes a successfully deployed model version from a source environment
        to a target environment. Enforces promotion validation checks.
        """
        source_job = await deployment_orchestrator.get_job(db, deployment_job_id)
        if not source_job:
            raise EntityNotFoundException(f"Source deployment job '{deployment_job_id}' not found.")

        if source_job.status != "succeeded":
            raise ValidationException(
                f"Cannot promote deployment job with status '{source_job.status}'. "
                "Only successful deployment jobs are eligible for promotion."
            )

        target_env = await environment_registry.get_environment(db, target_environment_id)
        if not target_env:
            raise EntityNotFoundException(f"Target environment '{target_environment_id}' not found.")

        logger.info(
            f"Promoting model version {source_job.model_version_id} "
            f"from environment {source_job.environment_id} to {target_environment_id}."
        )

        # Trigger deployment on the target environment
        promotion_job = await model_deployment_service.deploy_to_environment(
            db=db,
            environment_id=target_environment_id,
            model_version_id=source_job.model_version_id,
            deployed_by=promoted_by
        )

        return promotion_job


promotion_manager = PromotionManager()
