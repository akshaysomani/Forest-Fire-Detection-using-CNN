import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mlops import Release, DeploymentJob
from app.services.model_registry.model_repository import model_repository

logger = logging.getLogger("mlops.release_tracking_service")


class ReleaseTrackingService:
    @staticmethod
    async def audit_deployment_job(
        db: AsyncSession, job: DeploymentJob, action: str, performed_by: uuid.UUID, details: dict
    ) -> None:
        """Records an administrative audit log for deployment state changes."""
        from app.models.model_registry import ModelAuditLog

        # Log to the model registry audit logs for traceability
        await model_repository.create_audit_log(
            db=db,
            action=action,
            performed_by=performed_by,
            model_version_id=job.model_version_id,
            details={
                "deployment_job_id": str(job.id),
                "environment_id": str(job.environment_id),
                "status": job.status,
                **details,
            },
        )
        logger.info(f"Audited deployment action '{action}' on environment '{job.environment_id}' successfully.")


release_tracking_service = ReleaseTrackingService()
