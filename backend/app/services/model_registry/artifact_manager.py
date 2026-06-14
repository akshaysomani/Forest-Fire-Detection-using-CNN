import uuid
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_registry.artifact_repository import artifact_repository
from app.services.model_registry.artifact_storage_service import artifact_storage_service
from app.services.model_registry.model_repository import model_repository
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.model_registry import ModelArtifact
from app.models.training import TrainingRun, TrainingCheckpoint
from sqlalchemy import select, and_

logger = logging.getLogger("model_registry.artifact_manager")


class ArtifactManager:
    @staticmethod
    async def register_artifact(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        name: str,
        artifact_type: str,
        uri: str,
        created_by: Optional[uuid.UUID] = None,
    ) -> ModelArtifact:
        """
        Validates artifact file existence in storage, calculates file size and SHA256 checksum,
        and registers the record in the database.
        """
        # 1. Verify file exists in active storage
        if not await artifact_storage_service.verify_exists(uri):
            raise ValidationException(f"Artifact file not found in storage at URI: '{uri}'")

        # 2. Get file size and checksum
        file_size, checksum = await artifact_storage_service.get_file_metadata(uri)

        # 3. Create database entry
        artifact = await artifact_repository.create_artifact(
            db=db,
            model_version_id=model_version_id,
            name=name,
            artifact_type=artifact_type,
            uri=uri,
            file_size=file_size,
            checksum=checksum,
            created_by=created_by,
        )

        # 4. Audit Log entry
        await model_repository.create_audit_log(
            db=db,
            action="register_artifact",
            performed_by=created_by or uuid.UUID(int=0),
            model_version_id=model_version_id,
            details={"artifact_id": str(artifact.id), "name": name, "type": artifact_type, "uri": uri, "size": file_size},
        )

        return artifact

    @staticmethod
    async def auto_register_training_run_artifacts(
        db: AsyncSession, model_version_id: uuid.UUID, training_run_id: uuid.UUID, created_by: Optional[uuid.UUID] = None
    ) -> List[ModelArtifact]:
        """
        Auto-discovers and registers standard outputs of a training run:
        - Best model checkpoint file (weights)
        - Confusion Matrix plot (evaluation plot)
        - Evaluation Report Markdown (evaluation report)
        """
        # Fetch training run
        run = await db.get(TrainingRun, training_run_id)
        if not run or run.deleted_at is not None:
            raise EntityNotFoundException(f"Training run '{training_run_id}' not found.")

        # Find best checkpoint for this run
        checkpoint_query = (
            select(TrainingCheckpoint)
            .where(
                and_(
                    TrainingCheckpoint.run_id == training_run_id,
                    TrainingCheckpoint.is_best == True,
                    TrainingCheckpoint.deleted_at.is_(None),
                )
            )
            .limit(1)
        )
        res_checkpoint = await db.execute(checkpoint_query)
        checkpoint = res_checkpoint.scalar_one_or_none()

        if not checkpoint:
            # Fallback to latest checkpoint
            fallback_query = (
                select(TrainingCheckpoint)
                .where(and_(TrainingCheckpoint.run_id == training_run_id, TrainingCheckpoint.deleted_at.is_(None)))
                .order_by(TrainingCheckpoint.epoch.desc())
                .limit(1)
            )
            res_fallback = await db.execute(fallback_query)
            checkpoint = res_fallback.scalar_one_or_none()

        registered_artifacts = []

        # 1. Register Weights checkpoint (CRITICAL)
        if checkpoint:
            try:
                art = await ArtifactManager.register_artifact(
                    db=db,
                    model_version_id=model_version_id,
                    name=f"epoch_{checkpoint.epoch}_best_weights.pth",
                    artifact_type="weights",
                    uri=checkpoint.checkpoint_path,
                    created_by=created_by,
                )
                registered_artifacts.append(art)
            except Exception as e:
                logger.error(f"Failed to auto-register weights artifact: {str(e)}")
                raise ValidationException(f"Failed to register training checkpoint weights: {str(e)}")
        else:
            raise ValidationException(
                f"No checkpoint found for training run '{training_run_id}'. Cannot register model version."
            )

        # 2. Register Confusion Matrix (OPTIONAL/BEST EFFORT)
        cm_path = f"runs/{str(training_run_id)}/artifacts/confusion_matrix.png"
        if await artifact_storage_service.verify_exists(cm_path):
            try:
                art = await ArtifactManager.register_artifact(
                    db=db,
                    model_version_id=model_version_id,
                    name="confusion_matrix.png",
                    artifact_type="evaluation_plot",
                    uri=cm_path,
                    created_by=created_by,
                )
                registered_artifacts.append(art)
            except Exception as e:
                logger.warning(f"Failed to auto-register confusion matrix plot: {str(e)}")

        # 3. Register Evaluation Report (OPTIONAL/BEST EFFORT)
        report_path = f"runs/{str(training_run_id)}/artifacts/evaluation_report.md"
        if await artifact_storage_service.verify_exists(report_path):
            try:
                art = await ArtifactManager.register_artifact(
                    db=db,
                    model_version_id=model_version_id,
                    name="evaluation_report.md",
                    artifact_type="evaluation_report",
                    uri=report_path,
                    created_by=created_by,
                )
                registered_artifacts.append(art)
            except Exception as e:
                logger.warning(f"Failed to auto-register evaluation report: {str(e)}")

        return registered_artifacts


artifact_manager = ArtifactManager()
