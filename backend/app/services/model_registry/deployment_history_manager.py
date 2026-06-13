import uuid
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model_registry import ModelDeployment


class DeploymentHistoryManager:
    @staticmethod
    async def get_deployment_history_for_version(
        db: AsyncSession,
        model_version_id: uuid.UUID
    ) -> List[ModelDeployment]:
        """Lists all deployments (active or historical) for a model version."""
        query = select(ModelDeployment).where(
            and_(
                ModelDeployment.model_version_id == model_version_id,
                ModelDeployment.deleted_at.is_(None)
            )
        ).order_by(ModelDeployment.deployed_at.desc())
        res = await db.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def get_deployment_history_for_environment(
        db: AsyncSession,
        environment: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[ModelDeployment]:
        """Lists all deployments in a specific environment (e.g. production)."""
        query = select(ModelDeployment).where(
            and_(
                ModelDeployment.environment == environment.lower().strip(),
                ModelDeployment.deleted_at.is_(None)
            )
        ).order_by(ModelDeployment.deployed_at.desc()).offset(skip).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())


deployment_history_manager = DeploymentHistoryManager()
