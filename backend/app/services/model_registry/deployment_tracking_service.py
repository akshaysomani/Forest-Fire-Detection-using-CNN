import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_registry.model_repository import model_repository
from app.services.model_registry.lifecycle_workflow_engine import lifecycle_workflow_engine
from app.core.exceptions import ValidationException, EntityNotFoundException
from app.models.model_registry import ModelDeployment, ModelVersion, ModelArtifact

logger = logging.getLogger("model_registry.deployment_tracking_service")


class DeploymentTrackingService:
    @staticmethod
    async def deploy_version(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        environment: str,
        deployed_by: uuid.UUID,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ModelDeployment:
        """
        Deploys a model version to a target environment.
        Enforces approval gates, performs state transitions, creates deployment record,
        and dynamically hot-swaps inference weights in ModelManager.
        """
        version = await model_repository.get_version(db, model_version_id)
        if not version:
            raise EntityNotFoundException(f"Model version '{model_version_id}' not found.")

        env = environment.lower().strip()
        if env not in ("staging", "production"):
            raise ValidationException("Environment must be either 'staging' or 'production'.")

        # 1. Validation check on lifecycle state
        # Only Approved or Staging models can be promoted/deployed.
        if version.status not in ("Approved", "Staging", "Production"):
            raise ValidationException(
                f"Model version status is '{version.status}' and is not eligible for deployment. "
                "Version must be Approved, Staging, or Production."
            )

        # 2. Extract weights artifact
        art_query = (
            select(ModelArtifact)
            .where(
                and_(
                    ModelArtifact.model_version_id == model_version_id,
                    ModelArtifact.artifact_type == "weights",
                    ModelArtifact.deleted_at.is_(None),
                )
            )
            .limit(1)
        )
        res_art = await db.execute(art_query)
        weights_art = res_art.scalar_one_or_none()
        if not weights_art:
            raise ValidationException(f"Model version '{model_version_id}' has no registered weights checkpoint artifact.")

        # 3. Handle status transitions and governance
        target_state = "Staging" if env == "staging" else "Production"
        # Move version status to target state (triggers approval checks inside lifecycle engine)
        if version.status != target_state:
            await lifecycle_workflow_engine.trigger_transition(
                db=db,
                model_version_id=model_version_id,
                target_state=target_state,
                user_id=deployed_by,
                notes=f"Transitioning to {target_state} due to deployment on {env}.",
            )

        # 4. Create deployment record
        deployment = await model_repository.create_deployment(
            db=db,
            model_version_id=model_version_id,
            environment=env,
            status="active",
            deployed_by=deployed_by,
            metrics=metrics,
        )

        # 5. Hot-swap active inference model weights (if production environment)
        if env == "production":
            try:
                from app.services.inference.model_manager import model_manager

                # Resolve parent model name
                from app.models.model_registry import RegisteredModel

                m_query = select(RegisteredModel.name).where(RegisteredModel.id == version.model_id)
                res_m = await db.execute(m_query)
                model_name = res_m.scalar_one()

                await model_manager.load_and_set_active_model(
                    model_name=model_name, checkpoint_path=weights_art.uri, run_id=str(version.id)
                )
                logger.info(f"Successfully hot-swapped production model inference pointer to version {version.version}.")
            except Exception as e:
                logger.error(f"Failed to hot-swap active model weights in ModelManager: {str(e)}")
                # Mark deployment as failed
                deployment.status = "failed"
                await db.commit()
                raise ValidationException(f"Deployment succeeded in database but hot-swapping model failed: {str(e)}")

        # 6. Log Audit Action
        await model_repository.create_audit_log(
            db=db,
            action="deploy_model",
            performed_by=deployed_by,
            model_version_id=model_version_id,
            details={"deployment_id": str(deployment.id), "environment": env, "version": version.version},
        )

        return deployment

    @staticmethod
    async def rollback_deployment(
        db: AsyncSession, model_id: uuid.UUID, environment: str, performed_by: uuid.UUID
    ) -> ModelDeployment:
        """
        Rolls back the active deployment in an environment to the previous stable deployment.
        """
        env = environment.lower().strip()

        # 1. Resolve current active deployment
        current_active = await model_repository.get_active_deployment(db, model_id, env)
        if not current_active:
            raise ValidationException(f"No active deployment found for this model family in '{env}' to rollback.")

        # 2. Resolve previous deployment in line
        previous_deploy = await model_repository.get_previous_deployment(db, model_id, env)
        if not previous_deploy:
            raise ValidationException(f"No previous stable deployment found in '{env}' to rollback to.")

        # 3. Deactivate current active deployment
        current_active.status = "rolled_back"
        current_active.undeployed_at = datetime.utcnow()

        # Update current active model version to deprecated or staging depending on context
        curr_version = await model_repository.get_version(db, current_active.model_version_id)
        if curr_version:
            await lifecycle_workflow_engine.trigger_transition(
                db=db,
                model_version_id=curr_version.id,
                target_state="Deprecated",
                user_id=performed_by,
                notes=f"Deprecated automatically due to rollback in '{env}'.",
            )

        # 4. Activate previous deployment
        previous_deploy.status = "active"
        previous_deploy.undeployed_at = None

        prev_version = await model_repository.get_version(db, previous_deploy.model_version_id)
        if prev_version:
            target_state = "Staging" if env == "staging" else "Production"
            prev_version.status = target_state

            # Fetch weights artifact for previous version
            art_query = (
                select(ModelArtifact)
                .where(
                    and_(
                        ModelArtifact.model_version_id == prev_version.id,
                        ModelArtifact.artifact_type == "weights",
                        ModelArtifact.deleted_at.is_(None),
                    )
                )
                .limit(1)
            )
            res_art = await db.execute(art_query)
            weights_art = res_art.scalar_one_or_none()

            if not weights_art:
                raise ValidationException(f"Previous version '{prev_version.id}' has no registered weights artifact.")

            # 5. Hot-swap active weights to previous version
            if env == "production":
                try:
                    from app.models.model_registry import RegisteredModel

                    m_query = select(RegisteredModel.name).where(RegisteredModel.id == prev_version.model_id)
                    res_m = await db.execute(m_query)
                    prev_model_name = res_m.scalar_one()

                    from app.services.inference.model_manager import model_manager

                    await model_manager.load_and_set_active_model(
                        model_name=prev_model_name, checkpoint_path=weights_art.uri, run_id=str(prev_version.id)
                    )
                except Exception as e:
                    logger.error(f"Failed to hot-swap rollback model weights in ModelManager: {str(e)}")
                    raise ValidationException(f"Rollback failed during weights hot-swapping: {str(e)}")

        await db.commit()

        # 6. Log Audit Action
        await model_repository.create_audit_log(
            db=db,
            action="rollback_deployment",
            performed_by=performed_by,
            model_version_id=previous_deploy.model_version_id,
            details={
                "environment": env,
                "rolled_back_from_version_id": str(current_active.model_version_id),
                "rolled_back_to_version_id": str(previous_deploy.model_version_id),
            },
        )

        return previous_deploy


deployment_tracking_service = DeploymentTrackingService()
