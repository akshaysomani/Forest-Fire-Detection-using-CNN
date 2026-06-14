import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident

logger = logging.getLogger("incident.incident_metrics")


class IncidentMetrics:
    async def get_active_ratios(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Compiles active ratios:
        - Ratio of active incidents (Open, Acknowledged, Assigned, In Progress, Escalated) vs Resolved/Closed
        """
        query = select(Incident).where(Incident.deleted_at.is_(None))
        res = await db.execute(query)
        incidents = res.scalars().all()

        total = len(incidents)
        if total == 0:
            return {"active_count": 0, "resolved_closed_count": 0, "active_ratio": 0.0}

        active_statuses = ["Open", "Acknowledged", "Assigned", "In Progress", "Escalated"]
        active_count = sum(1 for inc in incidents if inc.status in active_statuses)
        resolved_closed_count = total - active_count

        return {
            "active_count": active_count,
            "resolved_closed_count": resolved_closed_count,
            "active_ratio": round(active_count / total, 4),
        }

    async def get_timeline_metrics(self, db: AsyncSession, days: int = 7) -> List[Dict[str, Any]]:
        """
        Compiles chronological active count trend arrays for dashboard charts.
        """
        query = select(Incident).where(Incident.deleted_at.is_(None))
        res = await db.execute(query)
        incidents = res.scalars().all()

        now = datetime.now(timezone.utc)
        timeline = []

        for d in range(days - 1, -1, -1):
            target_date = (now - timedelta(days=d)).date()
            # Calculate active count on that specific day:
            # An incident was active on target_date if it was created on or before that day
            # and is either not resolved/closed yet or resolved/closed after that day.
            # (For simplicity and mockup/telemetry compatibility, we can scan our loaded incidents).
            active_on_day = 0
            for inc in incidents:
                created_date = inc.created_at.date()
                if created_date <= target_date:
                    # If it's currently active, it was active then
                    if inc.status not in ["Resolved", "Closed"]:
                        active_on_day += 1
                    else:
                        # If resolved/closed, check if resolution was after target_date
                        resolved_date = inc.updated_at.date()  # Simplified fallback
                        if resolved_date > target_date:
                            active_on_day += 1

            timeline.append({"date": target_date.isoformat(), "active_incidents": active_on_day})

        return timeline


incident_metrics = IncidentMetrics()
