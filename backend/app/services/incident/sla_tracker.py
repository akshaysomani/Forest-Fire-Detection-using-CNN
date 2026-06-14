import logging
from datetime import datetime, timezone
from typing import List, Dict
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident

logger = logging.getLogger("incident.sla_tracker")


class SLATracker:
    # Default SLA thresholds in minutes for dispatch acknowledgment
    SLA_THRESHOLDS = {"Critical": 15, "High": 30, "Medium": 60, "Low": 120, "Informational": 240}

    def get_threshold_minutes(self, severity: str) -> int:
        """Get the SLA threshold in minutes for a given severity."""
        return self.SLA_THRESHOLDS.get(severity, 60)

    def is_response_sla_breached(self, incident: Incident, current_time: datetime = None) -> bool:
        """
        Determines if an incident has breached its response SLA.
        Response SLA is breached if the incident is still in 'Open' or 'Assigned' status
        and the elapsed time since its creation exceeds the threshold.
        """
        if incident.status not in ["Open", "Assigned"]:
            return False

        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Ensure incident created_at has timezone info, or compare naively if naive
        created_at = incident.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        elapsed_seconds = (current_time - created_at).total_seconds()
        threshold_seconds = self.get_threshold_minutes(incident.severity) * 60

        is_breached = elapsed_seconds > threshold_seconds
        if is_breached:
            logger.warning(
                f"Incident {incident.id} ({incident.severity}) breached SLA. "
                f"Elapsed: {elapsed_seconds / 60:.1f}m, Threshold: {threshold_seconds / 60:.1f}m"
            )
        return is_breached

    async def get_active_breaches(self, db: AsyncSession) -> List[Incident]:
        """
        Queries all active incidents that are in 'Open' or 'Assigned' status
        and have exceeded their SLA response window.
        """
        query = select(Incident).where(and_(Incident.status.in_(["Open", "Assigned"]), Incident.deleted_at.is_(None)))
        res = await db.execute(query)
        incidents = res.scalars().all()

        current_time = datetime.now(timezone.utc)
        breached_incidents = []
        for incident in incidents:
            if self.is_response_sla_breached(incident, current_time):
                breached_incidents.append(incident)

        return breached_incidents


sla_tracker = SLATracker()
