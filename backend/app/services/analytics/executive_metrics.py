import logging
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, ResponseMember
from app.models.alert import Alert

logger = logging.getLogger("analytics.executive_metrics")


class ExecutiveMetrics:
    async def get_fire_hazard_level(self, db: AsyncSession) -> str:
        """Calculate overall state fire hazard level based on active incidents and alerts density."""
        active_incidents = select(func.count(Incident.id)).where(
            and_(Incident.status.not_in(["Resolved", "Closed"]), Incident.deleted_at.is_(None))
        )
        critical_alerts = select(func.count(Alert.id)).where(
            and_(Alert.status == "active", Alert.severity.in_(["Critical", "High"]), Alert.deleted_at.is_(None))
        )
        inc_res = await db.execute(active_incidents)
        alt_res = await db.execute(critical_alerts)

        inc_count = inc_res.scalar_one()
        alt_count = alt_res.scalar_one()

        score = (inc_count * 15) + (alt_count * 5)
        if score > 100:
            return "Extreme"
        elif score > 60:
            return "High"
        elif score > 25:
            return "Medium"
        return "Low"

    async def get_active_responders_ratio(self, db: AsyncSession) -> float:
        """Calculate the ratio of dispatched / busy response members to total members."""
        busy_q = select(func.count(ResponseMember.id)).where(
            and_(ResponseMember.is_available == False, ResponseMember.deleted_at.is_(None))
        )
        total_q = select(func.count(ResponseMember.id)).where(ResponseMember.deleted_at.is_(None))

        busy_res = await db.execute(busy_q)
        total_res = await db.execute(total_q)

        busy = busy_res.scalar_one()
        total = total_res.scalar_one()

        if total == 0:
            return 0.0
        return round(float(busy) / float(total), 4)


executive_metrics = ExecutiveMetrics()
