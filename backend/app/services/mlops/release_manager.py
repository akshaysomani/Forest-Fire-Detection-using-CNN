import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.mlops.release_registry import release_registry
from app.services.model_registry.model_repository import model_repository
from app.models.mlops import Release

logger = logging.getLogger("mlops.release_manager")


class ReleaseManager:
    @staticmethod
    async def create_new_release(
        db: AsyncSession,
        version: str,
        description: Optional[str] = None,
        model_version_id: Optional[uuid.UUID] = None,
        created_by: Optional[uuid.UUID] = None
    ) -> Release:
        """
        Registers a new system release.
        Auto-generates detailed release notes if a model version is linked.
        """
        release_notes = f"Release version {version} compiled at standard MLOps pipeline.\n"
        
        if model_version_id:
            from app.models.model_registry import ModelVersion
            model_ver = await model_repository.get_version(db, model_version_id)
            if model_ver:
                release_notes += f"\n### Model Details:\n"
                release_notes += f"- **Model Version:** {model_ver.version}\n"
                release_notes += f"- **Status:** {model_ver.status}\n"
                if model_ver.metrics:
                    release_notes += f"- **Evaluation Metrics:**\n"
                    for k, v in model_ver.metrics.items():
                        release_notes += f"  - {k}: {v}\n"
                if model_ver.hyperparameters:
                    release_notes += f"- **Hyperparameters:**\n"
                    for k, v in model_ver.hyperparameters.items():
                        release_notes += f"  - {k}: {v}\n"
            else:
                release_notes += f"- Warning: Linked model version '{model_version_id}' could not be verified in the registry."

        release = await release_registry.create_release(
            db=db,
            version=version,
            description=description,
            model_version_id=model_version_id,
            release_notes=release_notes,
            created_by=created_by
        )
        logger.info(f"Registered system release version {version} successfully.")
        return release


release_manager = ReleaseManager()
