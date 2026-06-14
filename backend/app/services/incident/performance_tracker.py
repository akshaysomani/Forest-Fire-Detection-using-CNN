import logging
from typing import Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import ResponseTeam, IncidentAssignment

logger = logging.getLogger("incident.performance_tracker")


class PerformanceTracker:
    async def get_specialty_performance(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Compiles performance metrics aggregated by team specialty:
        - average acknowledgment times
        - count of completed missions
        - count of rejected assignments
        """
        # Fetch all teams
        teams_q = select(ResponseTeam).where(ResponseTeam.deleted_at.is_(None))
        teams_res = await db.execute(teams_q)
        teams = teams_res.scalars().all()

        specialties: Dict[str, Dict[str, Any]] = {}

        from app.services.incident.response_tracking_service import response_tracking_service

        for team in teams:
            spec = team.specialty
            if spec not in specialties:
                specialties[spec] = {
                    "specialty": spec,
                    "total_teams": 0,
                    "total_assignments": 0,
                    "completed_missions": 0,
                    "rejected_assignments": 0,
                    "ack_speeds_sum": 0.0,
                    "ack_speeds_count": 0,
                }

            specialties[spec]["total_teams"] += 1

            # Get individual team stats
            stats = await response_tracking_service.get_team_performance(db, team.id)
            specialties[spec]["total_assignments"] += stats["total_assignments"]
            specialties[spec]["completed_missions"] += stats["completed_missions_count"]
            specialties[spec]["rejected_assignments"] += stats["assignments_by_status"].get("Rejected", 0)

            avg_speed = stats["avg_acknowledgment_speed_seconds"]
            if avg_speed > 0:
                specialties[spec]["ack_speeds_sum"] += avg_speed
                specialties[spec]["ack_speeds_count"] += 1

        results = []
        for spec, data in specialties.items():
            avg_ack = 0.0
            if data["ack_speeds_count"] > 0:
                avg_ack = data["ack_speeds_sum"] / data["ack_speeds_count"]

            results.append(
                {
                    "specialty": spec,
                    "total_teams": data["total_teams"],
                    "total_assignments": data["total_assignments"],
                    "completed_missions": data["completed_missions"],
                    "rejected_assignments": data["rejected_assignments"],
                    "avg_acknowledgment_speed_seconds": round(avg_ack, 2),
                }
            )

        return results


performance_tracker = PerformanceTracker()
