import uuid
import logging
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mlops import DeploymentJob

logger = logging.getLogger("mlops.deployment_monitor")


class DeploymentMonitor:
    @staticmethod
    async def get_total_deployments_count(db: AsyncSession) -> int:
        query = select(func.count(DeploymentJob.id)).where(DeploymentJob.deleted_at.is_(None))
        res = await db.execute(query)
        return res.scalar() or 0

    @staticmethod
    async def get_deployments_by_status_count(db: AsyncSession, status: str) -> int:
        query = select(func.count(DeploymentJob.id)).where(
            and_(
                DeploymentJob.status == status.strip().lower(),
                DeploymentJob.deleted_at.is_(None)
            )
        )
        res = await db.execute(query)
        return res.scalar() or 0

    @staticmethod
    async def get_average_duration_seconds(db: AsyncSession) -> float:
        query = select(func.avg(DeploymentJob.duration_seconds)).where(
            and_(
                DeploymentJob.status == "succeeded",
                DeploymentJob.deleted_at.is_(None)
            )
        )
        res = await db.execute(query)
        val = res.scalar()
        return float(val) if val is not None else 0.0


deployment_monitor = DeploymentMonitor()
