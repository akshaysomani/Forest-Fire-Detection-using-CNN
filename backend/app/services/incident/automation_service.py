import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, IncidentAssignment
from app.services.incident.escalation_manager import escalation_manager
from app.services.incident.emergency_workflow_engine import emergency_workflow_engine

logger = logging.getLogger("incident.automation_service")


class AutomationService:
    async def run_sla_and_escalation_checks(self, db: AsyncSession) -> int:
        """
        Scans active incidents and automatically escalates SLA breaches.
        Returns the number of escalated incidents.
        """
        logger.debug("Running background SLA and escalation checks...")
        escalated_count = await escalation_manager.auto_escalate_active_breaches(db)
        if escalated_count > 0:
            logger.info(f"Background check auto-escalated {escalated_count} incidents.")
        return escalated_count

    async def run_auto_dispatch_checks(self, db: AsyncSession) -> int:
        """
        Scans all Open incidents that do not have active/pending assignments
        and tries to auto-dispatch an available response team.
        Returns the number of new assignments created.
        """
        logger.debug("Running background auto-dispatch checks...")
        # 1. Get all incidents in Open status
        query = select(Incident).where(
            and_(
                Incident.status == "Open",
                Incident.deleted_at.is_(None)
            )
        )
        res = await db.execute(query)
        open_incidents = res.scalars().all()

        dispatch_count = 0
        for incident in open_incidents:
            # Check if this incident has any pending or accepted assignments
            check_assign_q = select(IncidentAssignment).where(
                and_(
                    IncidentAssignment.incident_id == incident.id,
                    IncidentAssignment.status.in_(["Pending", "Accepted"])
                )
            )
            assign_res = await db.execute(check_assign_q)
            if assign_res.scalar_one_or_none():
                # Already assigned/pending assignment, skip
                continue

            # Try to auto-dispatch
            success = await emergency_workflow_engine.auto_dispatch(db, incident)
            if success:
                dispatch_count += 1

        if dispatch_count > 0:
            logger.info(f"Background check auto-dispatched {dispatch_count} open incidents.")
        return dispatch_count


automation_service = AutomationService()
