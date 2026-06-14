import logging
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, IncidentEvent, IncidentAuditLog
from app.services.incident.incident_lifecycle_service import incident_lifecycle_service
from app.services.incident.incident_service import incident_service

logger = logging.getLogger("incident.escalation_manager")


class EscalationManager:
    async def escalate_incident(
        self, db: AsyncSession, incident_id: uuid.UUID, user_id: Optional[uuid.UUID] = None, reason: Optional[str] = None
    ) -> Incident:
        """
        Escalates an incident to 'Escalated' status.
        Increments severity priority (e.g. Medium -> High -> Critical) if not already Critical,
        performs the state transition using incident_lifecycle_service,
        and logs events/audits.
        """
        logger.info(f"Escalating incident {incident_id}. User: {user_id}. Reason: {reason}")

        # 1. Fetch incident
        incident = await incident_service.get_incident_by_id(db, incident_id)

        # 2. Bump severity priority if not already Critical
        old_severity = incident.severity
        new_severity = old_severity

        if old_severity == "Low":
            new_severity = "Medium"
        elif old_severity == "Medium":
            new_severity = "High"
        elif old_severity in ["High", "Informational"]:
            new_severity = "Critical"

        if new_severity != old_severity:
            logger.info(f"Escalation severity bump: {old_severity} -> {new_severity} on incident {incident.id}")
            incident.severity = new_severity
            db.add(incident)

            # Record event for severity bump
            sev_event = IncidentEvent(
                incident_id=incident.id,
                event_type="incident_severity_escalated",
                payload={
                    "old_severity": old_severity,
                    "new_severity": new_severity,
                    "escalated_by": str(user_id) if user_id else "system",
                },
            )
            db.add(sev_event)

        # 3. Perform the status transition to 'Escalated'
        transition_reason = reason or f"Escalation triggered. Severity bumped: {old_severity} -> {new_severity}."
        incident = await incident_lifecycle_service.transition_status(
            db=db, incident_id=incident_id, new_status="Escalated", user_id=user_id, reason=transition_reason
        )

        # 4. Insert incident audit log for escalation action
        audit = IncidentAuditLog(
            incident_id=incident.id,
            user_id=user_id,
            action="incident_escalated",
            details={
                "escalated_by": str(user_id) if user_id else "system",
                "old_severity": old_severity,
                "new_severity": new_severity,
                "reason": transition_reason,
            },
        )
        db.add(audit)
        await db.flush()

        logger.info(f"Incident {incident_id} successfully escalated. Severity: {new_severity}")
        return incident

    async def auto_escalate_active_breaches(self, db: AsyncSession) -> int:
        """
        Scans for active SLA breaches and automatically escalates them.
        Returns the number of incidents escalated.
        """
        from app.services.incident.sla_tracker import sla_tracker

        breaches = await sla_tracker.get_active_breaches(db)
        count = 0

        for incident in breaches:
            # Avoid re-escalating already escalated ones (though sla_tracker filters by Open/Assigned)
            if incident.status != "Escalated":
                try:
                    await self.escalate_incident(
                        db=db,
                        incident_id=incident.id,
                        user_id=None,
                        reason=f"System auto-escalation: SLA response threshold exceeded for severity '{incident.severity}'.",
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to auto-escalate incident {incident.id}: {str(e)}")

        return count


escalation_manager = EscalationManager()
