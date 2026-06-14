import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_registry.review_manager import review_manager
from app.services.model_registry.model_repository import model_repository
from app.models.model_registry import ModelApproval
from sqlalchemy import select, and_


class ApprovalService:
    @staticmethod
    async def request_approval(
        db: AsyncSession,
        model_version_id: uuid.UUID,
        requested_by: uuid.UUID,
        target_stage: str,
        request_notes: Optional[str] = None,
    ) -> ModelApproval:
        """Submits a model version for stage promotion review."""
        return await review_manager.create_approval_request(
            db=db,
            model_version_id=model_version_id,
            requested_by=requested_by,
            target_stage=target_stage,
            request_notes=request_notes,
        )

    @staticmethod
    async def review_approval(
        db: AsyncSession, approval_id: uuid.UUID, reviewed_by: uuid.UUID, status: str, review_notes: Optional[str] = None
    ) -> ModelApproval:
        """Completes review processing (approves/rejects) of a pending promotion request."""
        return await review_manager.submit_review(
            db=db, approval_id=approval_id, reviewed_by=reviewed_by, status=status, review_notes=review_notes
        )

    @staticmethod
    async def get_approvals_for_version(db: AsyncSession, model_version_id: uuid.UUID) -> List[ModelApproval]:
        """Lists historical and pending approval requests for a model version."""
        query = (
            select(ModelApproval)
            .where(and_(ModelApproval.model_version_id == model_version_id, ModelApproval.deleted_at.is_(None)))
            .order_by(ModelApproval.requested_at.desc())
        )
        res = await db.execute(query)
        return list(res.scalars().all())


approval_service = ApprovalService()
