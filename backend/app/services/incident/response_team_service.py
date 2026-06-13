import logging
import uuid
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import ResponseTeam, ResponseMember
from app.core.exceptions import EntityNotFoundException, ValidationException

logger = logging.getLogger("incident.response_team_service")


class ResponseTeamService:
    async def create_team(self, db: AsyncSession, name: str, specialty: str) -> ResponseTeam:
        """Creates a new ResponseTeam with a unique name."""
        logger.info(f"Creating response team: {name} ({specialty})")

        # Check name uniqueness
        dup_query = select(ResponseTeam).where(ResponseTeam.name == name, ResponseTeam.deleted_at.is_(None))
        res_dup = await db.execute(dup_query)
        if res_dup.scalar_one_or_none():
            raise ValidationException(f"Response team name '{name}' is already registered.")

        team = ResponseTeam(
            name=name,
            specialty=specialty,
            status="Active"
        )
        db.add(team)
        await db.flush()
        return team

    async def add_member_to_team(
        self,
        db: AsyncSession,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "Responder"
    ) -> ResponseMember:
        """Adds a user to a response team as a member."""
        logger.info(f"Adding user {user_id} to team {team_id} with role '{role}'")

        # Verify team exists
        team_q = select(ResponseTeam).where(ResponseTeam.id == team_id, ResponseTeam.deleted_at.is_(None))
        team_res = await db.execute(team_q)
        if not team_res.scalar_one_or_none():
            raise EntityNotFoundException("Response team not found.")

        # Verify user is not already in the same team
        dup_member_q = select(ResponseMember).where(
            and_(
                ResponseMember.team_id == team_id,
                ResponseMember.user_id == user_id,
                ResponseMember.deleted_at.is_(None)
            )
        )
        res_dup = await db.execute(dup_member_q)
        if res_dup.scalar_one_or_none():
            raise ValidationException("User is already a member of this response team.")

        member = ResponseMember(
            team_id=team_id,
            user_id=user_id,
            role=role,
            is_available=True
        )
        db.add(member)
        await db.flush()
        return member

    async def set_member_availability(
        self,
        db: AsyncSession,
        member_id: uuid.UUID,
        is_available: bool
    ) -> ResponseMember:
        """Toggles the availability status of a response member."""
        logger.info(f"Setting member {member_id} availability to {is_available}")

        query = select(ResponseMember).where(ResponseMember.id == member_id, ResponseMember.deleted_at.is_(None))
        res = await db.execute(query)
        member = res.scalar_one_or_none()

        if not member:
            raise EntityNotFoundException("Response member not found.")

        member.is_available = is_available
        db.add(member)
        await db.flush()
        return member

    async def list_teams(self, db: AsyncSession) -> List[ResponseTeam]:
        """Fetch all response teams (including nested members list)."""
        query = select(ResponseTeam).where(ResponseTeam.deleted_at.is_(None)).options(selectinload(ResponseTeam.members))
        res = await db.execute(query)
        return list(res.scalars().all())


response_team_service = ResponseTeamService()
