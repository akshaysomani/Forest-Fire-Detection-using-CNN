import uuid
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mlops import DeploymentJob, Environment
from app.core.exceptions import ValidationException, EntityNotFoundException
from app.services.mlops.release_tracking_service import release_tracking_service

logger = logging.getLogger("mlops.deployment_orchestrator")


class DeploymentOrchestrator:
    @staticmethod
    async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Optional[DeploymentJob]:
        query = select(DeploymentJob).where(and_(DeploymentJob.id == job_id, DeploymentJob.deleted_at.is_(None)))
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_job(
        db: AsyncSession, environment_id: uuid.UUID, model_version_id: uuid.UUID, deployed_by: uuid.UUID
    ) -> DeploymentJob:
        """Creates a pending deployment job record."""
        job = DeploymentJob(
            environment_id=environment_id,
            model_version_id=model_version_id,
            status="pending",
            steps=[
                {"name": "checkpoint_verification", "status": "pending", "timestamp": None},
                {"name": "container_dry_run", "status": "pending", "timestamp": None},
                {"name": "traffic_shifting_10", "status": "pending", "timestamp": None},
                {"name": "traffic_shifting_100", "status": "pending", "timestamp": None},
            ],
            deployed_by=deployed_by,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def execute_job(db: AsyncSession, job_id: uuid.UUID) -> DeploymentJob:
        """
        Orchestrates and executes a step-by-step model deployment job.
        Simulates canary and build dry-runs for validation.
        """
        job = await DeploymentOrchestrator.get_job(db, job_id)
        if not job:
            raise EntityNotFoundException(f"DeploymentJob '{job_id}' not found.")

        if job.status != "pending":
            raise ValidationException(f"Cannot execute deployment job in state '{job.status}'.")

        logger.info(f"Starting execution of deployment job {job.id}.")
        job.status = "running"
        await db.commit()

        start_time = time.time()

        # Step 1: Checkpoint verification
        job.steps[0]["status"] = "running"
        job.steps[0]["timestamp"] = str(time.time())
        flag_modified(job, "steps")
        await db.commit()
        time.sleep(0.1)  # Simulate verification
        job.steps[0]["status"] = "completed"

        # Step 2: Container dry run
        job.steps[1]["status"] = "running"
        job.steps[1]["timestamp"] = str(time.time())
        flag_modified(job, "steps")
        await db.commit()
        time.sleep(0.1)
        job.steps[1]["status"] = "completed"

        # Step 3: Traffic Shifting 10%
        job.steps[2]["status"] = "running"
        job.steps[2]["timestamp"] = str(time.time())
        flag_modified(job, "steps")
        await db.commit()
        time.sleep(0.1)
        job.steps[2]["status"] = "completed"

        # Step 4: Traffic Shifting 100%
        job.steps[3]["status"] = "running"
        job.steps[3]["timestamp"] = str(time.time())
        flag_modified(job, "steps")
        await db.commit()
        time.sleep(0.1)
        job.steps[3]["status"] = "completed"

        # Complete
        job.status = "succeeded"
        job.duration_seconds = int(time.time() - start_time)
        flag_modified(job, "steps")
        await db.commit()
        await db.refresh(job)

        # Audit deployment success
        await release_tracking_service.audit_deployment_job(
            db=db,
            job=job,
            action="execute_deployment_success",
            performed_by=job.deployed_by,
            details={"duration": job.duration_seconds},
        )

        return job

    @staticmethod
    async def fail_job(db: AsyncSession, job_id: uuid.UUID, reason: str) -> DeploymentJob:
        """Sets deployment job to failed state."""
        job = await DeploymentOrchestrator.get_job(db, job_id)
        if not job:
            raise EntityNotFoundException(f"DeploymentJob '{job_id}' not found.")

        job.status = "failed"
        job.metrics = {"failure_reason": reason}
        await db.commit()
        await db.refresh(job)

        await release_tracking_service.audit_deployment_job(
            db=db, job=job, action="execute_deployment_failed", performed_by=job.deployed_by, details={"reason": reason}
        )

        return job


deployment_orchestrator = DeploymentOrchestrator()
