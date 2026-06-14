import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.models.token import RefreshToken
from app.services.jwt_service import jwt_service


class TokenManager:
    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash token using SHA-256 for secure database storage."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_refresh_token_record(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        parent_token_hash: str | None = None,
        expires_delta: timedelta | None = None,
    ) -> tuple[str, RefreshToken]:
        """Creates a new refresh token string and commits its hash to the database."""
        jti = uuid.uuid4()
        token_str = jwt_service.create_refresh_token(user_id=user_id, jti=jti, expires_delta=expires_delta)
        token_hash = self._hash_token(token_str)

        if expires_delta:
            expires_at = datetime.now(timezone.utc) + expires_delta
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        db_token = RefreshToken(
            id=jti,
            user_id=user_id,
            token_hash=token_hash,
            parent_token_hash=parent_token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        db.add(db_token)
        await db.flush()
        return token_str, db_token

    async def rotate_refresh_token(self, db: AsyncSession, refresh_token_str: str) -> tuple[str, str]:
        """Rotates a refresh token. Implements security checks to detect token reuse attacks.

        Returns:
            tuple[new_access_token_str, new_refresh_token_str]
        """
        # Validate token payload first
        payload = jwt_service.verify_token(refresh_token_str, expected_type="refresh")
        user_id_str = payload.get("sub")
        jti_str = payload.get("jti")

        if not user_id_str or not jti_str:
            raise AuthenticationException("Invalid token payload.")

        user_id = uuid.UUID(user_id_str)
        token_hash = self._hash_token(refresh_token_str)

        # Lookup token in database
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(query)
        db_token = result.scalar_one_or_none()

        # Security check: Token does not exist or has already been revoked
        if (
            not db_token
            or db_token.is_revoked
            or db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
        ):
            if db_token and db_token.is_revoked:
                # Potential Token Reuse Attack!
                # Revoke all descendants and ancestors of this rotation chain to protect user
                await self.revoke_entire_chain(db, db_token.user_id, token_hash)
                await db.commit()
                raise AuthenticationException("Refresh token has already been used. Session terminated.")
            raise AuthenticationException("Invalid or expired refresh token.")

        # Revoke the current token
        db_token.is_revoked = True
        db.add(db_token)

        # Generate a new refresh token with rotation
        new_refresh_token_str, new_db_token = await self.create_refresh_token_record(
            db, user_id=user_id, parent_token_hash=token_hash
        )

        # Update user session association if exists
        from app.models.session import UserSession

        session_query = select(UserSession).where(UserSession.refresh_token_id == db_token.id)
        session_result = await db.execute(session_query)
        session = session_result.scalar_one_or_none()
        if session:
            session.refresh_token_id = new_db_token.id
            session.last_activity_at = datetime.now(timezone.utc)
            db.add(session)

        # Create new access token
        # Get user email
        from app.models.user import User

        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationException("User is inactive or not found.")

        new_access_token_str = jwt_service.create_access_token(user_id=user_id, email=user.email)

        await db.flush()
        return new_access_token_str, new_refresh_token_str

    async def revoke_refresh_token(self, db: AsyncSession, refresh_token_str: str) -> None:
        """Revokes a refresh token and its session."""
        token_hash = self._hash_token(refresh_token_str)
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(query)
        db_token = result.scalar_one_or_none()

        if db_token:
            db_token.is_revoked = True
            db.add(db_token)

            # Deactivate any associated sessions
            from app.models.session import UserSession

            session_stmt = update(UserSession).where(UserSession.refresh_token_id == db_token.id).values(is_active=False)
            await db.execute(session_stmt)
            await db.flush()

    async def revoke_entire_chain(self, db: AsyncSession, user_id: uuid.UUID, root_token_hash: str) -> None:
        """Revokes all tokens for a user when token reuse is detected."""
        # Revoke all tokens for safety
        stmt = update(RefreshToken).where(RefreshToken.user_id == user_id).values(is_revoked=True)
        await db.execute(stmt)

        # Deactivate all active sessions for the user
        from app.models.session import UserSession

        session_stmt = update(UserSession).where(UserSession.user_id == user_id).values(is_active=False)
        await db.execute(session_stmt)
        await db.flush()


token_manager = TokenManager()
