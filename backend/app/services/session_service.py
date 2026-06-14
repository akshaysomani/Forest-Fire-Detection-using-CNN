import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.session import UserSession


class SessionService:
    @staticmethod
    def _parse_device_type(user_agent: str | None) -> str:
        if not user_agent:
            return "Unknown"
        ua = user_agent.lower()
        if "mobi" in ua or "android" in ua or "iphone" in ua:
            return "Mobile"
        if "tablet" in ua or "ipad" in ua:
            return "Tablet"
        return "Desktop"

    async def create_session(
        self, db: AsyncSession, user_id: uuid.UUID, refresh_token_id: uuid.UUID, ip_address: str | None, user_agent: str | None
    ) -> UserSession:
        """Tracks a new login session linked to a specific refresh token."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        device_type = self._parse_device_type(user_agent)

        session = UserSession(
            user_id=user_id,
            refresh_token_id=refresh_token_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
            is_active=True,
            expires_at=expires_at,
            last_activity_at=datetime.now(timezone.utc),
        )
        db.add(session)
        await db.flush()
        return session

    async def get_active_sessions(self, db: AsyncSession, user_id: uuid.UUID) -> list[UserSession]:
        """Returns all active sessions for a user."""
        query = select(UserSession).where(
            UserSession.user_id == user_id, UserSession.is_active == True, UserSession.expires_at > datetime.now(timezone.utc)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def revoke_session(self, db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Terminates a specific session for a user, revoking the associated refresh token."""
        query = select(UserSession).where(UserSession.id == session_id, UserSession.user_id == user_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session or not session.is_active:
            return False

        session.is_active = False
        db.add(session)

        # Revoke the associated refresh token if it exists
        if session.refresh_token_id:
            from app.models.token import RefreshToken

            token_stmt = update(RefreshToken).where(RefreshToken.id == session.refresh_token_id).values(is_revoked=True)
            await db.execute(token_stmt)

        await db.flush()
        return True

    async def revoke_all_sessions(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        """Revokes all active sessions and refresh tokens for a user (e.g. on password change)."""
        # Revoke sessions
        session_stmt = (
            update(UserSession).where(UserSession.user_id == user_id, UserSession.is_active == True).values(is_active=False)
        )
        await db.execute(session_stmt)

        # Revoke tokens
        from app.models.token import RefreshToken

        token_stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
            .values(is_revoked=True)
        )
        await db.execute(token_stmt)

        await db.flush()

    async def update_session_activity(self, db: AsyncSession, session_id: uuid.UUID) -> None:
        """Updates the last activity timestamp for a session."""
        stmt = update(UserSession).where(UserSession.id == session_id).values(last_activity_at=datetime.now(timezone.utc))
        await db.execute(stmt)
        await db.flush()


session_service = SessionService()
