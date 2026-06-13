import uuid
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import SecurityEvent, CompliancePolicy
from app.models.user import User


class RiskEngine:
    async def calculate_user_risk_score(self, db: AsyncSession, user_id: uuid.UUID) -> float:
        """
        Calculate user risk score on a 0.0 - 10.0 scale:
        - Base: 0.0
        - Failed login attempts (0.5 each, max 3.0)
        - Locked account (add 3.0)
        - Unverified email (add 1.0)
        - High-severity security events involving user (add 2.0 each, max 4.0)
        """
        q = select(User).where(User.id == user_id)
        res = await db.execute(q)
        user = res.scalar_one_or_none()

        if not user:
            return 0.0

        score = 0.0

        # Failed attempts
        score += min(user.failed_login_attempts * 0.5, 3.0)

        # Locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            score += 3.0

        # Unverified
        if not user.is_verified:
            score += 1.0

        # Fetch recent user security events
        q_events = select(SecurityEvent).where(SecurityEvent.user_id == user_id, SecurityEvent.severity.in_(["HIGH", "CRITICAL"]))
        res_events = await db.execute(q_events)
        high_severity_events = res_events.scalars().all()
        score += min(len(high_severity_events) * 2.0, 4.0)

        return min(score, 10.0)

    async def calculate_system_risk_score(self, db: AsyncSession) -> float:
        """
        Calculate global system risk score on a 0.0 - 10.0 scale:
        - Base: 0.0
        - Active non-compliant policies (add 2.0 per policy)
        - Number of blocked IPs (add 0.5 per IP, max 3.0)
        - Open high-severity incidents (add 1.5 per incident, max 4.0)
        """
        score = 0.0

        # Policies
        q_pol = select(CompliancePolicy).where(CompliancePolicy.status == "NON_COMPLIANT")
        res_pol = await db.execute(q_pol)
        non_compliant_count = len(res_pol.scalars().all())
        score += non_compliant_count * 2.0

        # Blocked IPs
        from app.services.security.api_security_service import api_security_service
        blocked_ips = api_security_service.get_blocked_ips()
        score += min(len(blocked_ips) * 0.5, 3.0)

        # Active Incidents
        from app.services.security.security_incident_tracker import security_incident_tracker
        active_incidents = await security_incident_tracker.get_active_incidents(db)
        score += min(len(active_incidents) * 1.5, 4.0)

        return min(score, 10.0)


from datetime import datetime
risk_engine = RiskEngine()
