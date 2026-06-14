import logging
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, ResponseTeam

logger = logging.getLogger("incident.assignment_manager")


class AssignmentManager:
    async def suggest_best_team_for_incident(self, db: AsyncSession, incident: Incident) -> Optional[ResponseTeam]:
        """
        Suggests the most suitable active team for an incident.
        Prioritizes:
        1. Specialty matching (e.g. 'Wildfire Suppression' for High/Critical severity).
        2. Status is Active, is available (current_incident_id is None).
        3. Falls back to any available active team.
        """
        severity = incident.severity
        preferred_specialty = "Wildfire Suppression" if severity in ["Critical", "High"] else "General Dispatch"

        # 1. Try to find preferred specialty available team
        query = select(ResponseTeam).where(
            and_(
                ResponseTeam.status == "Active",
                ResponseTeam.specialty == preferred_specialty,
                ResponseTeam.current_incident_id.is_(None),
                ResponseTeam.deleted_at.is_(None),
            )
        )
        res = await db.execute(query)
        team = res.scalar_one_or_none()

        if team:
            logger.info(f"Suggested specialty team '{team.name}' ({team.specialty}) for incident {incident.id}")
            return team

        # 2. Fallback to any active available team
        fallback_query = select(ResponseTeam).where(
            and_(
                ResponseTeam.status == "Active", ResponseTeam.current_incident_id.is_(None), ResponseTeam.deleted_at.is_(None)
            )
        )
        res_fb = await db.execute(fallback_query)
        team_fb = res_fb.scalar_one_or_none()

        if team_fb:
            logger.info(f"Suggested fallback team '{team_fb.name}' ({team_fb.specialty}) for incident {incident.id}")
            return team_fb

        logger.warning(f"No available response teams found to assign to incident {incident.id}")
        return None


assignment_manager = AssignmentManager()
