import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mlops import DeploymentJob, Environment, Release
from app.services.mlops.deployment_orchestrator import deployment_orchestrator
from app.services.mlops.environment_registry import environment_registry
from app.services.mlops.release_manager import release_manager
from app.services.model_registry.model_repository import model_repository
from app.services.model_registry.deployment_tracking_service import deployment_tracking_service
from app.core.exceptions import ValidationException, EntityNotFoundException

logger = logging.getLogger("mlops.model_deployment_service")


class ModelDeploymentService:
    @staticmethod
    async def deploy_to_environment(
        db: AsyncSession,
        environment_id: uuid.UUID,
        model_version_id: uuid.UUID,
        deployed_by: uuid.UUID
    ) -> DeploymentJob:
        """
        Orchestrates the entire model deployment process onto a target environment.
        Executes canary workflows, updates environment tables, and triggers hot-swapping.
        """
        # 1. Resolve environment
        env = await environment_registry.get_environment(db, environment_id)
        if not env:
            raise EntityNotFoundException(f"Environment '{environment_id}' not found.")

        # 2. Resolve version
        version = await model_repository.get_version(db, model_version_id)
        if not version:
            raise EntityNotFoundException(f"Model version '{model_version_id}' not found.")

        # 3. Create and execute deployment job
        job = await deployment_orchestrator.create_job(
            db=db,
            environment_id=environment_id,
            model_version_id=model_version_id,
            deployed_by=deployed_by
        )

        try:
            # Execute step-by-step canary/build pipelines
            job = await deployment_orchestrator.execute_job(db, job.id)
        except Exception as e:
            logger.error(f"Deployment orchestrator failed: {str(e)}")
            job = await deployment_orchestrator.fail_job(db, job.id, str(e))
            raise ValidationException(f"Deployment execution failed: {str(e)}")

        # 4. Perform weights loading & environment updating if job succeeded
        if job.status == "succeeded":
            try:
                # Trigger model registry deployment tracking (which handles hot-swapping)
                await deployment_tracking_service.deploy_version(
                    db=db,
                    model_version_id=model_version_id,
                    environment=env.name,
                    deployed_by=deployed_by,
                    metrics=version.metrics
                )
                
                # Register a system release
                release_ver = f"release-{env.name}-{version.version}"
                
                # Check if release with this version already exists, if so append unique suffix
                existing_release = await db.execute(
                    select(Release)
                    .where(Release.version == release_ver)
                )
                if existing_release.scalar_one_or_none():
                    import random
                    release_ver += f"-{random.randint(1000, 9999)}"

                release = await release_manager.create_new_release(
                    db=db,
                    version=release_ver,
                    description=f"Auto-release for model {version.version} deployed to {env.name}.",
                    model_version_id=model_version_id,
                    created_by=deployed_by
                )

                # Link environment to the release
                await environment_registry.update_environment_release(db, environment_id, release.id)

            except Exception as ex:
                logger.error(f"Post-deployment registry or hot-swap task failed: {str(ex)}")
                job = await deployment_orchestrator.fail_job(db, job.id, f"Post-deploy task failed: {str(ex)}")
                raise ValidationException(f"Post-deployment hot-swapping failed: {str(ex)}")

        await db.refresh(job)
        return job

    @staticmethod
    async def rollback_environment(
        db: AsyncSession,
        environment_id: uuid.UUID,
        performed_by: uuid.UUID
    ) -> DeploymentJob:
        """
        Rolls back the active deployment in an environment to the previous stable release.
        """
        env = await environment_registry.get_environment(db, environment_id)
        if not env:
            raise EntityNotFoundException(f"Environment '{environment_id}' not found.")

        # Query previous deployment job in this environment
        from sqlalchemy import select, desc, and_
        query = select(DeploymentJob).where(
            and_(
                DeploymentJob.environment_id == environment_id,
                DeploymentJob.status == "succeeded",
                DeploymentJob.deleted_at.is_(None)
            )
        ).order_by(desc(DeploymentJob.created_at))
        res = await db.execute(query)
        jobs = res.scalars().all()

        if len(jobs) < 2:
            raise ValidationException("No previous stable deployment found in this environment to rollback to.")

        # Previous successful job is at index 1
        previous_job = jobs[1]

        # Trigger deployment of previous version to this environment
        rollback_job = await ModelDeploymentService.deploy_to_environment(
            db=db,
            environment_id=environment_id,
            model_version_id=previous_job.model_version_id,
            deployed_by=performed_by
        )

        # Set job rollback details
        rollback_job.rollback_job_id = previous_job.id
        await db.commit()
        await db.refresh(rollback_job)

        return rollback_job


# Import statement to make sure we don't hit circular import on Select
from sqlalchemy import select
model_deployment_service = ModelDeploymentService()
