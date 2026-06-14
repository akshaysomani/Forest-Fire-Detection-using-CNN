import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_registry.model_repository import model_repository
from app.services.model_registry.state_manager import state_manager
from app.core.exceptions import ValidationException, EntityNotFoundException
from app.models.model_registry import ModelVersion, ModelApproval
from sqlalchemy import select, and_

logger = logging.getLogger("model_registry.lifecycle_workflow_engine")


class LifecycleWorkflowEngine:
    @staticmethod
    async def trigger_transition(
        db: AsyncSession, model_version_id: uuid.UUID, target_state: str, user_id: uuid.UUID, notes: Optional[str] = None
    ) -> ModelVersion:
        """
        Transitions the model version state if valid.
        Runs validation checks for transition gates.
        """
        # 1. Fetch version
        version = await model_repository.get_version(db, model_version_id)
        if not version:
            raise EntityNotFoundException(f"Model version '{model_version_id}' not found.")

        old_status = version.status
        new_status = target_state.strip().capitalize()

        # 2. Run state-machine validation
        state_manager.validate_transition(old_status, new_status)

        # 3. Transition Gate Validations
        if new_status == "Approved":
            # Must have validation metrics and accuracy recorded
            if not version.metrics or "accuracy" not in version.metrics:
                raise ValidationException("Model version cannot be approved without evaluation metrics.")
            # Verify weights artifact exists
            # Verify weights artifact exists
            from app.models.model_registry import ModelArtifact

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
            has_weights = res_art.scalar_one_or_none() is not None
            if not has_weights:
                raise ValidationException("Model version cannot be approved without a registered weights checkpoint artifact.")

        elif new_status == "Production":
            # Promotion to production requires an approved ModelApproval request
            # if the model wasn't already in Approved or Staging status.
            if old_status not in ("Approved", "Staging"):
                approval_query = (
                    select(ModelApproval)
                    .where(
                        and_(
                            ModelApproval.model_version_id == model_version_id,
                            ModelApproval.target_stage == "Production",
                            ModelApproval.status == "approved",
                            ModelApproval.deleted_at.is_(None),
                        )
                    )
                    .limit(1)
                )
                res_approval = await db.execute(approval_query)
                approval = res_approval.scalar_one_or_none()
                if not approval:
                    raise ValidationException("Model version promotion to Production requires an approved review workflow.")

        # 4. Perform Transition
        version.status = new_status
        await db.commit()

        # 5. Log lifecycle event
        await model_repository.create_lifecycle_event(
            db=db,
            model_version_id=model_version_id,
            from_state=old_status,
            to_state=new_status,
            triggered_by=user_id,
            notes=notes,
        )

        # 6. Log Audit Trail
        await model_repository.create_audit_log(
            db=db,
            action="transition_state",
            performed_by=user_id,
            model_version_id=model_version_id,
            details={"from_state": old_status, "to_state": new_status, "notes": notes},
        )

        return version


lifecycle_workflow_engine = LifecycleWorkflowEngine()
