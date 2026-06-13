import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_registry.lifecycle_workflow_engine import lifecycle_workflow_engine
from app.services.model_registry.model_repository import model_repository
from app.models.model_registry import ModelVersion, ModelLifecycleEvent
from sqlalchemy import select, and_


class ModelLifecycleService:
    @staticmethod
    async def transition_model_version(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        target_state: str,
        user_id: uuid.UUID,
        notes: Optional[str] = None
    ) -> ModelVersion:
        """Transitions a model version to a target lifecycle state."""
        return await lifecycle_workflow_engine.trigger_transition(
            db=db,
            model_version_id=model_version_id,
            target_state=target_state,
            user_id=user_id,
            notes=notes
        )

    @staticmethod
    async def get_lifecycle_history(
        db: AsyncSession,
        model_version_id: uuid.UUID
    ) -> List[ModelLifecycleEvent]:
        """Retrieves transition event history logs for a model version."""
        query = select(ModelLifecycleEvent).where(
            and_(
                ModelLifecycleEvent.model_version_id == model_version_id,
                ModelLifecycleEvent.deleted_at.is_(None)
            )
        ).order_by(ModelLifecycleEvent.created_at.asc())
        res = await db.execute(query)
        return list(res.scalars().all())


model_lifecycle_service = ModelLifecycleService()
