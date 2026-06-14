import uuid
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model_registry import ModelDeployment, ModelVersion


class DeploymentRegistry:
    @staticmethod
    async def list_active_deployments(db: AsyncSession) -> List[ModelDeployment]:
        """Lists active deployments across all environments."""
        query = (
            select(ModelDeployment)
            .where(and_(ModelDeployment.status == "active", ModelDeployment.deleted_at.is_(None)))
            .order_by(ModelDeployment.deployed_at.desc())
        )
        res = await db.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def get_active_deployment_for_model(
        db: AsyncSession, model_id: uuid.UUID, environment: str
    ) -> Optional[ModelDeployment]:
        """Resolves the current active deployment for a model family in an environment."""
        # Find all versions for the model
        versions_query = select(ModelVersion.id).where(
            and_(ModelVersion.model_id == model_id, ModelVersion.deleted_at.is_(None))
        )
        res_vids = await db.execute(versions_query)
        vids = list(res_vids.scalars().all())
        if not vids:
            return None

        query = (
            select(ModelDeployment)
            .where(
                and_(
                    ModelDeployment.model_version_id.in_(vids),
                    ModelDeployment.environment == environment.lower().strip(),
                    ModelDeployment.status == "active",
                    ModelDeployment.deleted_at.is_(None),
                )
            )
            .order_by(ModelDeployment.deployed_at.desc())
            .limit(1)
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()


deployment_registry = DeploymentRegistry()
