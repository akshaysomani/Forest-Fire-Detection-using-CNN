import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_registry.model_repository import model_repository
from app.services.model_registry.model_registry_service import model_registry_service
from app.models.model_registry import ModelVersion

logger = logging.getLogger("model_registry.model_registry_manager")


class ModelRegistryManager:
    @staticmethod
    async def register_training_run_result(
        db: AsyncSession,
        training_run_id: uuid.UUID,
        model_name: str,
        user_id: uuid.UUID,
        description: Optional[str] = None
    ) -> ModelVersion:
        """
        Orchestrates auto-creating a model family and registering its training run result
        in one command.
        """
        # 1. Resolve or register the model family
        model_name_clean = model_name.strip().lower()
        model = await model_repository.get_model_by_name(db, model_name_clean)
        
        if not model:
            logger.info(f"Model family '{model_name_clean}' not found. Auto-registering family definition.")
            model = await model_registry_service.register_model(
                db=db,
                name=model_name_clean,
                description=f"Auto-generated model family for {model_name_clean}.",
                user_id=user_id
            )

        # 2. Register version
        version = await model_registry_service.register_model_version(
            db=db,
            model_id=model.id,
            training_run_id=training_run_id,
            checkpoint_id=None,
            description=description or f"Auto-registered from training run {training_run_id}.",
            release_notes="Auto-registered version.",
            user_id=user_id,
            increment_type="patch"
        )

        return version


model_registry_manager = ModelRegistryManager()
