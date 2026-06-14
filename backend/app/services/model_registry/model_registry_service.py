import uuid
import logging
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.services.model_registry.model_repository import model_repository
from app.services.model_registry.version_manager import version_manager
from app.services.model_registry.artifact_manager import artifact_manager
from app.services.model_registry.model_comparator import model_comparator
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.model_registry import (
    RegisteredModel,
    ModelVersion,
    ModelArtifact,
    ModelMetadata,
    ModelDeployment,
    ModelApproval,
    ModelLifecycleEvent,
)
from app.models.training import TrainingRun, TrainingCheckpoint

logger = logging.getLogger("model_registry.model_registry_service")


class ModelRegistryService:
    @staticmethod
    async def register_model(
        db: AsyncSession, name: str, description: Optional[str] = None, user_id: Optional[uuid.UUID] = None
    ) -> RegisteredModel:
        """Registers a new model definition family."""
        name_clean = name.strip().lower()
        if not name_clean:
            raise ValidationException("Model name cannot be empty.")

        existing = await model_repository.get_model_by_name(db, name_clean)
        if existing:
            raise ValidationException(f"Model family with name '{name_clean}' is already registered.")

        model = await model_repository.create_model(db=db, name=name_clean, description=description, created_by=user_id)

        await model_repository.create_audit_log(
            db=db,
            action="register_model_family",
            performed_by=user_id or uuid.UUID(int=0),
            details={"model_id": str(model.id), "name": name_clean},
        )
        return model

    @staticmethod
    async def register_model_version(
        db: AsyncSession,
        model_id: uuid.UUID,
        training_run_id: Optional[uuid.UUID] = None,
        checkpoint_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        release_notes: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        increment_type: str = "patch",
    ) -> ModelVersion:
        """
        Registers a new version of a model.
        Automatically resolves semantic version increment, binds hyperparameters/metrics,
        creates the record in status 'Draft', and registers associated training artifacts.
        """
        model = await model_repository.get_model(db, model_id)
        if not model:
            raise EntityNotFoundException(f"Model family '{model_id}' not found.")

        # 1. Resolve run and checkpoint metadata
        metrics = {}
        hyperparameters = {}

        if training_run_id:
            run = await db.get(TrainingRun, training_run_id)
            if not run or run.deleted_at is not None:
                raise EntityNotFoundException(f"Training run '{training_run_id}' not found.")

            # Fetch hyperparams
            hyperparameters = run.hyperparameters or {}

            # Resolve metrics from latest or best checkpoint
            checkpoint_query = select(TrainingCheckpoint).where(
                and_(TrainingCheckpoint.run_id == training_run_id, TrainingCheckpoint.deleted_at.is_(None))
            )
            if checkpoint_id:
                checkpoint_query = checkpoint_query.where(TrainingCheckpoint.id == checkpoint_id)
            else:
                # Prefer best checkpoint
                checkpoint_query = checkpoint_query.order_by(
                    TrainingCheckpoint.is_best.desc(), TrainingCheckpoint.epoch.desc()
                )

            checkpoint_query = checkpoint_query.limit(1)
            res_cp = await db.execute(checkpoint_query)
            cp = res_cp.scalar_one_or_none()

            if cp:
                checkpoint_id = cp.id
                metrics = {
                    "val_loss": cp.val_loss,
                    "val_accuracy": cp.val_accuracy,
                    "accuracy": cp.val_accuracy,
                    "loss": cp.val_loss,
                    "epoch": cp.epoch,
                }

        # 2. Resolve version string
        version_str = await version_manager.resolve_next_version(db, model_id, increment_type)

        # 3. Create ModelVersion in DB
        version = await model_repository.create_version(
            db=db,
            model_id=model_id,
            version_str=version_str,
            training_run_id=training_run_id,
            checkpoint_id=checkpoint_id,
            status="Draft",
            created_by=user_id,
            description=description,
            release_notes=release_notes,
            metrics=metrics,
            hyperparameters=hyperparameters,
        )

        # 4. Auto-register artifacts from training run
        if training_run_id:
            try:
                await artifact_manager.auto_register_training_run_artifacts(
                    db=db, model_version_id=version.id, training_run_id=training_run_id, created_by=user_id
                )
            except Exception as e:
                logger.error(f"Artifact auto-registration encountered an issue: {str(e)}")
                # We do not crash the version creation, but log the failure.
                # However, if critical weights are missing, it might raise ValidationException (handled inside auto_register)

        # 5. Log audit action
        await model_repository.create_audit_log(
            db=db,
            action="register_model_version",
            performed_by=user_id or uuid.UUID(int=0),
            model_version_id=version.id,
            details={"version": version_str, "status": "Draft"},
        )

        # 6. Log dynamic lifecycle event
        await model_repository.create_lifecycle_event(
            db=db,
            model_version_id=version.id,
            from_state="Draft",
            to_state="Draft",
            triggered_by=user_id or uuid.UUID(int=0),
            notes="Initial version registration.",
        )

        return version

    @staticmethod
    async def get_model_version_details(db: AsyncSession, version_id: uuid.UUID) -> ModelVersion:
        """
        Retrieves detailed model version information including
        nested artifacts, deployments, approvals, and lifecycle event histories.
        """
        from sqlalchemy.orm import selectinload

        query = (
            select(ModelVersion)
            .options(
                selectinload(ModelVersion.artifacts),
                selectinload(ModelVersion.deployments),
                selectinload(ModelVersion.approvals),
                selectinload(ModelVersion.lifecycle_events),
                selectinload(ModelVersion.metadata_items),
            )
            .where(and_(ModelVersion.id == version_id, ModelVersion.deleted_at.is_(None)))
        )
        res = await db.execute(query)
        version = res.scalar_one_or_none()

        if not version:
            raise EntityNotFoundException(f"Model version '{version_id}' not found.")

        return version

    @staticmethod
    async def compare_versions(db: AsyncSession, version_id_a: uuid.UUID, version_id_b: uuid.UUID) -> Dict[str, Any]:
        """Compares two model versions compiling metrics and configurations differences."""
        version_a = await model_repository.get_version(db, version_id_a)
        version_b = await model_repository.get_version(db, version_id_b)

        if not version_a:
            raise EntityNotFoundException(f"Model version '{version_id_a}' not found.")
        if not version_b:
            raise EntityNotFoundException(f"Model version '{version_id_b}' not found.")

        comparison = model_comparator.compare_versions(version_a, version_b)
        comparison["version_a"] = version_a
        comparison["version_b"] = version_b
        return comparison


model_registry_service = ModelRegistryService()
