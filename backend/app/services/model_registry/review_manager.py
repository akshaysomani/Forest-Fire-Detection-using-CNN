import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_registry.model_repository import model_repository
from app.services.model_registry.model_governance_engine import model_governance_engine
from app.services.model_registry.lifecycle_workflow_engine import lifecycle_workflow_engine
from app.core.exceptions import ValidationException, EntityNotFoundException
from app.models.model_registry import ModelApproval, ModelVersion
from sqlalchemy import select, and_


class ReviewManager:
    @staticmethod
    async def create_approval_request(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        requested_by: uuid.UUID,
        target_stage: str,
        request_notes: Optional[str] = None
    ) -> ModelApproval:
        """
        Creates a new model approval request for stage promotion.
        Runs governance compliance policies before permitting the request.
        """
        version = await model_repository.get_version(db, model_version_id)
        if not version:
            raise EntityNotFoundException(f"Model version '{model_version_id}' not found.")

        # Ensure model is in Draft or Validation state
        if version.status not in ("Draft", "Validation"):
            raise ValidationException(
                f"Cannot request approval for version in status '{version.status}'. "
                "Version must be in 'Draft' or 'Validation' state."
            )

        # Run automated governance policy checks
        is_compliant, failures = model_governance_engine.evaluate_governance_policies(version)
        if not is_compliant:
            raise ValidationException(
                f"Model version failed automated governance check. Issues: {', '.join(failures)}"
            )

        # Deactivate any active pending approvals for this version & stage
        deact_query = select(ModelApproval).where(
            and_(
                ModelApproval.model_version_id == model_version_id,
                ModelApproval.target_stage == target_stage,
                ModelApproval.status == "pending",
                ModelApproval.deleted_at.is_(None)
            )
        )
        res_deact = await db.execute(deact_query)
        pending_list = res_deact.scalars().all()
        for p in pending_list:
            p.status = "rejected"
            p.review_notes = "Superseded by a new approval request."
            p.reviewed_at = datetime_now()  # We can set to current time
        await db.commit()

        approval = await model_repository.create_approval(
            db=db,
            model_version_id=model_version_id,
            requested_by=requested_by,
            target_stage=target_stage,
            request_notes=request_notes
        )

        # Transition model version to 'Validation' status if it was in 'Draft'
        if version.status == "Draft":
            await lifecycle_workflow_engine.trigger_transition(
                db=db,
                model_version_id=model_version_id,
                target_state="Validation",
                user_id=requested_by,
                notes="Automatically moved to Validation on approval request."
            )

        # Log audit action
        await model_repository.create_audit_log(
            db=db,
            action="request_approval",
            performed_by=requested_by,
            model_version_id=model_version_id,
            details={
                "approval_id": str(approval.id),
                "target_stage": target_stage,
                "notes": request_notes
            }
        )

        return approval

    @staticmethod
    async def submit_review(
        db: AsyncSession,
        approval_id: uuid.UUID,
        reviewed_by: uuid.UUID,
        status: str,
        review_notes: Optional[str] = None
    ) -> ModelApproval:
        """
        Completes the review workflow for a model version.
        If status is 'approved', triggers the version promotion state transition.
        """
        approval = await model_repository.get_approval(db, approval_id)
        if not approval:
            raise EntityNotFoundException(f"Approval request '{approval_id}' not found.")

        if approval.status != "pending":
            raise ValidationException(f"Approval request is already processed. Status: '{approval.status}'")

        status_norm = status.lower().strip()
        if status_norm not in ("approved", "rejected"):
            raise ValidationException("Review outcome must be 'approved' or 'rejected'.")

        from datetime import datetime
        approval.status = status_norm
        approval.reviewed_by = reviewed_by
        approval.reviewed_at = datetime.utcnow()
        approval.review_notes = review_notes
        await db.commit()

        # If approved, transition model version
        if status_norm == "approved":
            # Target stage is generally Approved, Staging, or Production
            target_state = approval.target_stage
            # Wait: if target_stage is Production, we transition to Approved first, or directly to Production?
            # Wait, let's allow transitioning directly to Approved or Staging, and Production will check for this approval.
            # Let's transition the version status to target_state
            await lifecycle_workflow_engine.trigger_transition(
                db=db,
                model_version_id=approval.model_version_id,
                target_state=target_state,
                user_id=reviewed_by,
                notes=f"Promoted to {target_state} via approved review workflow: {review_notes or ''}"
            )
        else:
            # If rejected, transition model version back to Draft
            await lifecycle_workflow_engine.trigger_transition(
                db=db,
                model_version_id=approval.model_version_id,
                target_state="Draft",
                user_id=reviewed_by,
                notes=f"Reverted to Draft due to review rejection: {review_notes or ''}"
            )

        # Log audit action
        await model_repository.create_audit_log(
            db=db,
            action="submit_review",
            performed_by=reviewed_by,
            model_version_id=approval.model_version_id,
            details={
                "approval_id": str(approval.id),
                "outcome": status_norm,
                "notes": review_notes
            }
        )

        return approval


# Inline datetime helper
def datetime_now():
    from datetime import datetime
    return datetime.utcnow()


review_manager = ReviewManager()
