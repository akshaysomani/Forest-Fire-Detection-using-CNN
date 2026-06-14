import logging
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert, AlertAuditLog
from app.services.alert.alert_priority_manager import alert_priority_manager
from app.services.alert.event_bus import event_bus

logger = logging.getLogger("alert.escalation_service")


class EscalationService:
    async def check_and_escalate_alerts(self, db: AsyncSession) -> List[Alert]:
        """
        Scans for active alerts that have breached SLA response thresholds,
        updates status to 'escalated', logs the action, and dispatches an escalation event.
        """
        logger.debug("Running alert SLA escalation scan...")

        # 1. Fetch active alerts
        query = select(Alert).where(and_(Alert.status == "active", Alert.deleted_at.is_(None)))
        res = await db.execute(query)
        active_alerts = res.scalars().all()

        escalated_alerts = []

        for alert in active_alerts:
            # 2. Check if SLA threshold has been breached
            if alert_priority_manager.is_sla_breached(alert.severity, alert.created_at):
                logger.info(f"Alert {alert.id} ({alert.severity}) has breached SLA. Escalaing...")

                # 3. Update status
                alert.status = "escalated"
                db.add(alert)

                # 4. Audit Log
                audit = AlertAuditLog(
                    alert_id=alert.id,
                    action="alert_escalated",
                    details={"severity": alert.severity, "created_at": alert.created_at.isoformat()},
                )
                db.add(audit)

                # 5. Publish to Event Bus
                event_payload = {
                    "alert_id": str(alert.id),
                    "severity": alert.severity,
                    "message": f"ESCALATED: {alert.message}",
                }
                await event_bus.publish("alert_escalated", event_payload)

                escalated_alerts.append(alert)

        if escalated_alerts:
            await db.flush()
            logger.info(f"Escalated {len(escalated_alerts)} alerts during SLA scan.")

        return escalated_alerts


escalation_service = EscalationService()
