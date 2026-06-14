import logging
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import ResponseTeam

logger = logging.getLogger("incident.team_registry")


class TeamRegistry:
    async def get_active_teams(self, db: AsyncSession) -> List[ResponseTeam]:
        """Fetch all response teams marked as Active."""
        query = select(ResponseTeam).where(ResponseTeam.status == "Active", ResponseTeam.deleted_at.is_(None))
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_available_teams_by_specialty(self, db: AsyncSession, specialty: str) -> List[ResponseTeam]:
        """Fetch active teams under a specific specialty that are not currently occupied."""
        query = select(ResponseTeam).where(
            and_(
                ResponseTeam.status == "Active",
                ResponseTeam.specialty == specialty,
                ResponseTeam.current_incident_id.is_(None),
                ResponseTeam.deleted_at.is_(None),
            )
        )
        res = await db.execute(query)
        return list(res.scalars().all())


team_registry = TeamRegistry()
