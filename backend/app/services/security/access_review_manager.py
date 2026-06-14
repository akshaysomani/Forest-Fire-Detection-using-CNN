import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import AccessReviewCampaign, AccessReviewDecision, SecurityEvent
from app.models.user import User
from app.models.role import Role
from app.services.security.identity_governance_service import identity_governance_service
from app.core.exceptions import ValidationException


class AccessReviewManager:
    async def create_campaign(
        self, db: AsyncSession, name: str, target_role: Optional[str] = None, current_user_id: Optional[uuid.UUID] = None
    ) -> AccessReviewCampaign:
        """Create a new access certification campaign."""
        # Ensure there are no other active campaigns with same name
        q = select(AccessReviewCampaign).where(AccessReviewCampaign.name == name, AccessReviewCampaign.status == "ACTIVE")
        res = await db.execute(q)
        if res.scalar_one_or_none():
            raise ValidationException(f"An active access review campaign with name '{name}' already exists.")

        campaign = AccessReviewCampaign(name=name, status="ACTIVE", target_role=target_role, created_by_id=current_user_id)
        db.add(campaign)
        await db.flush()

        # Security event log
        event = SecurityEvent(
            event_type="ACCESS_REVIEW_CAMPAIGN_STARTED",
            severity="INFO",
            description=f"Access review campaign '{name}' (Target Role: {target_role or 'ALL'}) started by user ID {current_user_id}",
            user_id=current_user_id,
            details_json={"campaign_id": str(campaign.id), "campaign_name": name, "target_role": target_role},
        )
        db.add(event)
        return campaign

    async def submit_decision(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        decision_type: str,  # 'CERTIFIED' or 'REVOKED'
        justification: Optional[str] = None,
    ) -> AccessReviewDecision:
        """Submit a reviewer decision for a user role assignment."""
        # Validate campaign is active
        q_camp = select(AccessReviewCampaign).where(AccessReviewCampaign.id == campaign_id)
        res_camp = await db.execute(q_camp)
        campaign = res_camp.scalar_one_or_none()
        if not campaign or campaign.status != "ACTIVE":
            raise ValidationException("Campaign not found or is no longer active.")

        # Validate target user and role
        q_user = select(User).where(User.id == user_id, User.deleted_at.is_(None)).options(selectinload(User.roles))
        res_user = await db.execute(q_user)
        user = res_user.scalar_one_or_none()
        if not user:
            raise ValidationException("User not found.")

        q_role = select(Role).where(Role.id == role_id)
        res_role = await db.execute(q_role)
        role = res_role.scalar_one_or_none()
        if not role:
            raise ValidationException("Role not found.")

        # Verify role matches campaign target if target_role is specified
        if campaign.target_role and role.name != campaign.target_role:
            raise ValidationException(f"Campaign only accepts reviews for role '{campaign.target_role}'.")

        # Verify user has the role
        if role not in user.roles:
            raise ValidationException(f"User does not possess role '{role.name}'.")

        # Check if decision already exists for this user/role/campaign
        q_decision = select(AccessReviewDecision).where(
            AccessReviewDecision.campaign_id == campaign_id,
            AccessReviewDecision.user_id == user_id,
            AccessReviewDecision.role_id == role_id,
        )
        res_dec = await db.execute(q_decision)
        existing = res_dec.scalar_one_or_none()

        if existing:
            existing.decision = decision_type
            existing.reviewer_id = reviewer_id
            existing.decision_date = datetime.utcnow()
            existing.justification = justification
            decision = existing
        else:
            decision = AccessReviewDecision(
                campaign_id=campaign_id,
                user_id=user_id,
                role_id=role_id,
                reviewer_id=reviewer_id,
                decision=decision_type,
                justification=justification,
            )
            db.add(decision)

        await db.flush()

        # Enforce revocation immediately if REVOKED
        if decision_type == "REVOKED":
            await identity_governance_service.revoke_role_from_user(
                db, user_id=user_id, role_name=role.name, current_user_id=reviewer_id
            )

        # Audit
        event = SecurityEvent(
            event_type="ACCESS_REVIEW_DECISION_SUBMITTED",
            severity="INFO" if decision_type == "CERTIFIED" else "WARNING",
            description=f"Access review decision: '{decision_type}' for user {user.username} with role '{role.name}' under campaign '{campaign.name}' by reviewer ID {reviewer_id}",
            user_id=reviewer_id,
            details_json={
                "campaign_id": str(campaign_id),
                "target_user_id": str(user_id),
                "role_name": role.name,
                "decision": decision_type,
                "justification": justification,
            },
        )
        db.add(event)

        return decision

    async def complete_campaign(
        self, db: AsyncSession, campaign_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> AccessReviewCampaign:
        """Mark access review campaign as completed."""
        q = select(AccessReviewCampaign).where(AccessReviewCampaign.id == campaign_id)
        res = await db.execute(q)
        campaign = res.scalar_one_or_none()
        if not campaign:
            raise ValidationException("Campaign not found.")

        if campaign.status == "COMPLETED":
            return campaign

        campaign.status = "COMPLETED"
        campaign.completed_at = datetime.utcnow()
        db.add(campaign)
        await db.flush()

        # Log
        event = SecurityEvent(
            event_type="ACCESS_REVIEW_CAMPAIGN_COMPLETED",
            severity="INFO",
            description=f"Access review campaign '{campaign.name}' has been marked as COMPLETED by user ID {current_user_id}",
            user_id=current_user_id,
            details_json={"campaign_id": str(campaign_id), "campaign_name": campaign.name},
        )
        db.add(event)
        return campaign


access_review_manager = AccessReviewManager()
