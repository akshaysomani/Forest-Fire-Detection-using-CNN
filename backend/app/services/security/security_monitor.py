import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.security.risk_engine import risk_engine
from app.services.security.threat_analyzer import threat_analyzer
from app.models.security import SecurityEvent

logger = logging.getLogger("security.monitor")


class SecurityMonitor:
    async def evaluate_security_health(self, db: AsyncSession) -> dict:
        """
        Check risk thresholds and emit critical alerts if required:
        - Evaluates global system risk score.
        - Generates event if score exceeds 7.5.
        """
        risk_score = await risk_engine.calculate_system_risk_score(db)
        threat_report = await threat_analyzer.analyze_threats(db)

        # Trigger critical security event if system risk goes too high
        if risk_score >= 7.5:
            event = SecurityEvent(
                event_type="SYSTEM_RISK_THRESHOLD_EXCEEDED",
                severity="CRITICAL",
                description=f"Global system security risk score reached critical level: {risk_score}",
                details_json={"risk_score": risk_score, "threats_summary": threat_report},
            )
            db.add(event)
            await db.commit()
            logger.error(f"[SECURITY_ALERT] Critical system risk threshold exceeded: {risk_score}")

        return {
            "system_risk_score": risk_score,
            "threats_count": threat_report["total_threats"],
            "blocked_ips": threat_report["blocked_ips_count"],
            "status": "CRITICAL" if risk_score >= 7.5 else "WARNING" if risk_score >= 4.0 else "HEALTHY",
        }


security_monitor = SecurityMonitor()
