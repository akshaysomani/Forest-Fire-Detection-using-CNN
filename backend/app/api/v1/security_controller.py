import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_active_user, PermissionChecker
from app.models.user import User
from app.models.security import AccessReviewCampaign
from app.schemas.security_schema import (
    SecurityEventResponse,
    AccessReviewCampaignResponse,
    AccessReviewCampaignCreate,
    AccessReviewDecisionResponse,
    AccessReviewDecisionCreate,
    SecretMetadataResponse,
    SecretRotationRequest,
    CompliancePolicyResponse,
    ThreatResponse,
    GovernanceDashboardResponse
)
from app.services.security.permission_auditor import permission_auditor
from app.services.security.security_event_service import security_event_service
from app.services.security.compliance_manager import compliance_manager
from app.services.security.access_review_manager import access_review_manager
from app.services.security.credential_rotation_service import credential_rotation_service
from app.services.security.threat_analyzer import threat_analyzer
from app.services.security.governance_dashboard_service import governance_dashboard_service

router = APIRouter()


@router.get("/audit", status_code=status.HTTP_200_OK)
async def get_security_audit(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("access_audit_logs"))
):
    """Triggers and returns a system identity governance and permissions compliance audit."""
    findings = await permission_auditor.perform_security_audit(db, current_user.id)
    await db.commit()
    return findings


@router.get("/events", response_model=List[SecurityEventResponse], status_code=status.HTTP_200_OK)
async def get_security_events(
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("access_audit_logs"))
):
    """Retrieve historical security logs and SIEM telemetry metadata."""
    events = await security_event_service.get_events(
        db, severity=severity, event_type=event_type, skip=skip, limit=limit
    )
    return events


@router.get("/compliance", response_model=List[CompliancePolicyResponse], status_code=status.HTTP_200_OK)
async def get_compliance_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """Retrieve the current compliance verification scan statuses for GDPR and SOC2 frameworks."""
    # Seed if empty to avoid returning empty array
    await compliance_manager.seed_compliance_policies(db)
    await db.commit()
    policies = await compliance_manager.get_compliance_status(db)
    return policies


@router.post("/compliance/run/{policy_name}", response_model=CompliancePolicyResponse, status_code=status.HTTP_200_OK)
async def run_compliance_check(
    policy_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """Trigger an active compliance scanning run for the specified policy configuration."""
    policy = await compliance_manager.run_compliance_check(db, policy_name, current_user.id)
    await db.commit()
    return policy


@router.get("/access-reviews", response_model=List[AccessReviewCampaignResponse], status_code=status.HTTP_200_OK)
async def get_access_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_users"))
):
    """Fetch all registered access certification campaigns."""
    from sqlalchemy import select
    q = select(AccessReviewCampaign)
    res = await db.execute(q)
    return list(res.scalars().all())


@router.post("/access-reviews", response_model=AccessReviewCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_access_review_campaign(
    campaign_in: AccessReviewCampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_users"))
):
    """Creates a new active access review campaign."""
    campaign = await access_review_manager.create_campaign(
        db, name=campaign_in.name, target_role=campaign_in.target_role, current_user_id=current_user.id
    )
    await db.commit()
    return campaign


@router.post("/access-reviews/{campaign_id}/decisions", response_model=AccessReviewDecisionResponse, status_code=status.HTTP_201_CREATED)
async def submit_access_review_decision(
    campaign_id: uuid.UUID,
    decision_in: AccessReviewDecisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_users"))
):
    """Submits a certification or revocation decision for a user role assignment."""
    decision = await access_review_manager.submit_decision(
        db,
        campaign_id=campaign_id,
        user_id=decision_in.user_id,
        role_id=decision_in.role_id,
        reviewer_id=current_user.id,
        decision_type=decision_in.decision,
        justification=decision_in.justification
    )
    await db.commit()
    return decision


@router.post("/rotate-secrets", response_model=SecretMetadataResponse, status_code=status.HTTP_200_OK)
async def rotate_secrets(
    req: SecretRotationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """Trigger credentials rotation cycle for the specified key."""
    # Ensure secrets metadata are seeded
    from app.services.security.secret_manager import secret_manager
    await secret_manager.initialize_and_seed_secrets(db)
    await db.commit()

    secret = await credential_rotation_service.rotate_secret(
        db, key=req.key, rotated_by_id=current_user.id
    )
    await db.commit()
    return secret


@router.get("/threats", response_model=ThreatResponse, status_code=status.HTTP_200_OK)
async def get_threat_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("access_audit_logs"))
):
    """Retrieve active threats indicators, blocked IP counts, and security violations."""
    threat_report = await threat_analyzer.analyze_threats(db)
    return threat_report


@router.get("/governance", response_model=GovernanceDashboardResponse, status_code=status.HTTP_200_OK)
async def get_governance_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports"))
):
    """Fetch high-level safety risk scores, compliance ratings, and review completions."""
    # Initialize dependent secrets and policies if empty to prevent score calculations mismatch
    from app.services.security.secret_manager import secret_manager
    await secret_manager.initialize_and_seed_secrets(db)
    await compliance_manager.seed_compliance_policies(db)
    await db.commit()

    summary = await governance_dashboard_service.get_dashboard_summary(db)
    return summary
