import uuid
import logging
from typing import Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.training import TrainingRun, TrainingCheckpoint
from app.core.exceptions import EntityNotFoundException

logger = logging.getLogger("inference.model_registry_adapter")


class ModelRegistryAdapter:
    @staticmethod
    async def get_checkpoint_by_run(db: AsyncSession, run_id: uuid.UUID, epoch: Optional[int] = None) -> Tuple[str, str]:
        """
        Query the database to resolve the checkpoint path and model name for a training run.
        If epoch is not specified, resolves the 'best' checkpoint (is_best=True) or the latest epoch.
        Returns a tuple of (model_name, checkpoint_path).
        """
        # 1. Fetch training run
        run_query = select(TrainingRun).where(and_(TrainingRun.id == run_id, TrainingRun.deleted_at.is_(None)))
        res = await db.execute(run_query)
        run = res.scalar_one_or_none()
        if not run:
            raise EntityNotFoundException(f"Training run with ID '{run_id}' not found.")

        # 2. Query checkpoint
        if epoch is not None:
            checkpoint_query = select(TrainingCheckpoint).where(
                and_(
                    TrainingCheckpoint.run_id == run_id,
                    TrainingCheckpoint.epoch == epoch,
                    TrainingCheckpoint.deleted_at.is_(None),
                )
            )
        else:
            # Prefer best checkpoint
            checkpoint_query = (
                select(TrainingCheckpoint)
                .where(
                    and_(
                        TrainingCheckpoint.run_id == run_id,
                        TrainingCheckpoint.is_best == True,
                        TrainingCheckpoint.deleted_at.is_(None),
                    )
                )
                .limit(1)
            )

        res_checkpoint = await db.execute(checkpoint_query)
        checkpoint = res_checkpoint.scalar_one_or_none()

        # Fallback to latest epoch if no best checkpoint is flagged
        if not checkpoint and epoch is None:
            fallback_query = (
                select(TrainingCheckpoint)
                .where(and_(TrainingCheckpoint.run_id == run_id, TrainingCheckpoint.deleted_at.is_(None)))
                .order_by(TrainingCheckpoint.epoch.desc())
                .limit(1)
            )
            res_fallback = await db.execute(fallback_query)
            checkpoint = res_fallback.scalar_one_or_none()

        if not checkpoint:
            raise EntityNotFoundException(f"No valid checkpoint found for training run '{run_id}'.")

        return run.model_name, checkpoint.checkpoint_path

    @staticmethod
    async def get_latest_completed_run_checkpoint(db: AsyncSession, model_name: Optional[str] = None) -> Tuple[str, str, str]:
        """
        Resolves the checkpoint path for the latest completed training run.
        Filters by model_name if provided.
        Returns a tuple of (run_id_str, model_name, checkpoint_path).
        """
        query = select(TrainingRun).where(and_(TrainingRun.status == "completed", TrainingRun.deleted_at.is_(None)))
        if model_name:
            query = query.where(TrainingRun.model_name == model_name)

        query = query.order_by(TrainingRun.completed_at.desc()).limit(1)
        res = await db.execute(query)
        run = res.scalar_one_or_none()

        if not run:
            raise EntityNotFoundException("No completed training runs found in registry.")

        # Find best checkpoint for this run
        checkpoint_query = (
            select(TrainingCheckpoint)
            .where(
                and_(
                    TrainingCheckpoint.run_id == run.id,
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
                .where(and_(TrainingCheckpoint.run_id == run.id, TrainingCheckpoint.deleted_at.is_(None)))
                .order_by(TrainingCheckpoint.epoch.desc())
                .limit(1)
            )
            res_fallback = await db.execute(fallback_query)
            checkpoint = res_fallback.scalar_one_or_none()

        if not checkpoint:
            raise EntityNotFoundException(f"No checkpoint found for completed run '{run.id}'.")

        return str(run.id), run.model_name, checkpoint.checkpoint_path


model_registry_adapter = ModelRegistryAdapter()
