import logging
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mlops import DeploymentJob

logger = logging.getLogger("mlops.deployment_metrics")


class DeploymentMetrics:
    @staticmethod
    async def get_rollback_frequency(db: AsyncSession) -> float:
        """Returns the ratio of rolled back deployment jobs to total deployments."""
        total_query = select(func.count(DeploymentJob.id)).where(DeploymentJob.deleted_at.is_(None))
        rollback_query = select(func.count(DeploymentJob.id)).where(
            and_(
                DeploymentJob.rollback_job_id.is_not(None),
                DeploymentJob.deleted_at.is_(None)
            )
        )

        res_total = await db.execute(total_query)
        total = res_total.scalar() or 0

        if total == 0:
            return 0.0

        res_rollback = await db.execute(rollback_query)
        rollbacks = res_rollback.scalar() or 0

        return float(rollbacks) / float(total)

    @staticmethod
    async def get_release_stability_index(db: AsyncSession) -> float:
        """
        Stability Index maps to ratio of succeeded deployments to total finished deployments.
        Expected scale: 0.0 to 1.0.
        """
        total_query = select(func.count(DeploymentJob.id)).where(
            and_(
                DeploymentJob.status.in_(["succeeded", "failed"]),
                DeploymentJob.deleted_at.is_(None)
            )
        )
        succeeded_query = select(func.count(DeploymentJob.id)).where(
            and_(
                DeploymentJob.status == "succeeded",
                DeploymentJob.deleted_at.is_(None)
            )
        )

        res_total = await db.execute(total_query)
        total = res_total.scalar() or 0

        if total == 0:
            return 1.0  # Safe default if no deployments yet

        res_succeeded = await db.execute(succeeded_query)
        succeeded = res_succeeded.scalar() or 0

        return float(succeeded) / float(total)


deployment_metrics = DeploymentMetrics()
