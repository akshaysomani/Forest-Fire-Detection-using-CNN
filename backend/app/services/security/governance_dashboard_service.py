from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import (
    AccessReviewCampaign,
    AccessReviewDecision,
    SecretMetadata,
    SecretRotationLog,
    CompliancePolicy,
    SecurityEvent
)
from app.services.security.risk_engine import risk_engine
from app.services.security.api_security_service import api_security_service


class GovernanceDashboardService:
    async def get_dashboard_summary(self, db: AsyncSession) -> dict:
        """
        Aggregate critical corporate security and identity metrics for administrative console:
        - System Risk Score (derived from active threats and compliance)
        - Compliance health percent
        - Active threat counter
        - Pending Access certification reviews count
        - Date of last secret rotation run
        """
        # Global risk
        overall_risk_score = await risk_engine.calculate_system_risk_score(db)

        # Compliance score
        q_pol = select(CompliancePolicy)
        res_pol = await db.execute(q_pol)
        policies = res_pol.scalars().all()
        total_p = len(policies)
        compliant_p = sum(1 for p in policies if p.status == "COMPLIANT")
        compliance_score = (compliant_p / total_p * 100.0) if total_p > 0 else 100.0

        # Active threats (blocked IPs count)
        active_threats_count = len(api_security_service.get_blocked_ips())

        # Pending access reviews: campaigns that are ACTIVE
        q_camps = select(AccessReviewCampaign).where(AccessReviewCampaign.status == "ACTIVE")
        res_camps = await db.execute(q_camps)
        active_camps = res_camps.scalars().all()
        pending_access_reviews_count = len(active_camps)

        # Last secret rotation
        q_rot = select(SecretRotationLog).where(SecretRotationLog.status == "SUCCESS").order_by(desc(SecretRotationLog.rotated_at)).limit(1)
        res_rot = await db.execute(q_rot)
        last_rot_log = res_rot.scalar_one_or_none()
        last_secret_rotation = last_rot_log.rotated_at if last_rot_log else None

        # Status Summary
        status_summary = {
            "system_risk_level": "CRITICAL" if overall_risk_score >= 7.5 else "WARNING" if overall_risk_score >= 4.0 else "HEALTHY",
            "active_campaigns_count": len(active_camps),
            "total_registered_secrets": len((await db.execute(select(SecretMetadata))).scalars().all())
        }

        return {
            "overall_risk_score": overall_risk_score,
            "compliance_score": compliance_score,
            "active_threats_count": active_threats_count,
            "pending_access_reviews_count": pending_access_reviews_count,
            "last_secret_rotation": last_secret_rotation,
            "status_summary": status_summary
        }


governance_dashboard_service = GovernanceDashboardService()
