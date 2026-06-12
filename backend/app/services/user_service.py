import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    EntityNotFoundException,
    ValidationException,
    InvalidCredentialsException,
    AccountLockedException
)
from app.models.user import User
from app.models.role import Role
from app.models.audit import AuditLog
from app.repositories.user_repository import user_repository
from app.services.password_service import password_service
from app.services.password_validators import validate_password_strength
from app.services.session_service import session_service

FAILED_LIMIT = 5
LOCK_DURATION_MINUTES = 15


class UserService:
    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        user = await user_repository.get_by_id(db, user_id)
        if not user:
            raise EntityNotFoundException("User not found.")
        return user

    async def register_user(self, db: AsyncSession, user_in: dict) -> User:
        # Check duplicate email
        existing_email = await user_repository.get_by_email(db, user_in["email"])
        if existing_email:
            raise ValidationException("Email is already registered.")

        # Check duplicate username
        existing_username = await user_repository.get_by_username(db, user_in["username"])
        if existing_username:
            raise ValidationException("Username is already taken.")

        # Validate password strength
        validate_password_strength(user_in["password"])

        hashed_password = password_service.hash_password(user_in["password"])

        # Default role: Viewer
        query = select(Role).where(Role.name == "Viewer")
        res = await db.execute(query)
        viewer_role = res.scalar_one_or_none()

        # Seed roles if they do not exist
        if not viewer_role:
            from app.services.permission_service import permission_service
            await permission_service.seed_roles_and_permissions(db)
            query = select(Role).where(Role.name == "Viewer")
            res = await db.execute(query)
            viewer_role = res.scalar_one_or_none()

        db_user = User(
            email=user_in["email"],
            username=user_in["username"],
            hashed_password=hashed_password,
            profile_image_url=user_in.get("profile_image_url"),
            is_active=True,
            is_verified=False
        )

        if viewer_role:
            db_user.roles.append(viewer_role)

        db.add(db_user)
        await db.flush()

        # Create verification token
        token = password_service.generate_action_token(db_user.email, action="verify_email")
        db_user.email_verification_token = token
        db_user.email_verification_expires_at = datetime.utcnow() + timedelta(hours=24)
        db.add(db_user)

        # Audit log
        audit = AuditLog(
            user_id=db_user.id,
            action="user.register",
            resource_type="user",
            resource_id=str(db_user.id),
            details={"email": db_user.email, "username": db_user.username}
        )
        db.add(audit)

        await db.flush()
        return db_user

    async def authenticate_user(
        self,
        db: AsyncSession,
        identifier: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> User:
        user = await user_repository.get_by_email_or_username(db, identifier)
        if not user:
            raise InvalidCredentialsException()

        # Check account lockout status
        if user.locked_until and user.locked_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            raise AccountLockedException(
                f"Account is locked. Please try again after {user.locked_until.isoformat()} UTC."
            )

        # Verify password
        if not password_service.verify_password(password, user.hashed_password):
            # Track failed attempt
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= FAILED_LIMIT:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCK_DURATION_MINUTES)
                # Reset attempts on lock initiation to avoid overflow
                user.failed_login_attempts = 0

            db.add(user)

            # Audit failed login
            audit = AuditLog(
                user_id=user.id,
                action="user.login_failed",
                ip_address=ip_address,
                user_agent=user_agent,
                resource_type="user",
                resource_id=str(user.id),
                details={"reason": "incorrect_password", "failed_attempts_count": user.failed_login_attempts}
            )
            db.add(audit)
            await db.flush()
            raise InvalidCredentialsException()

        # Success path
        # Reset failed attempts and lockout
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        db.add(user)

        # Audit successful login
        audit = AuditLog(
            user_id=user.id,
            action="user.login",
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="user",
            resource_id=str(user.id)
        )
        db.add(audit)
        await db.flush()
        return user

    async def change_password(self, db: AsyncSession, user_id: uuid.UUID, data: dict) -> None:
        user = await self.get_by_id(db, user_id)

        if not password_service.verify_password(data["old_password"], user.hashed_password):
            raise ValidationException("Incorrect current password.")

        validate_password_strength(data["new_password"])

        user.hashed_password = password_service.hash_password(data["new_password"])
        db.add(user)

        # Force terminate all active sessions & refresh tokens on password change
        await session_service.revoke_all_sessions(db, user_id)

        # Audit password change
        audit = AuditLog(
            user_id=user.id,
            action="user.password_change",
            resource_type="user",
            resource_id=str(user.id)
        )
        db.add(audit)
        await db.flush()

    async def initiate_password_reset(self, db: AsyncSession, email: str) -> None:
        user = await user_repository.get_by_email(db, email)
        if not user:
            # Silence user enumeration attacks by returning success always
            return

        token = password_service.generate_action_token(email, action="reset_password", expires_in_minutes=30)
        user.password_reset_token = token
        user.password_reset_expires_at = datetime.utcnow() + timedelta(minutes=30)
        db.add(user)

        audit = AuditLog(
            user_id=user.id,
            action="user.password_reset_requested",
            resource_type="user",
            resource_id=str(user.id)
        )
        db.add(audit)
        await db.flush()

    async def execute_password_reset(self, db: AsyncSession, data: dict) -> None:
        email = password_service.verify_action_token(data["token"], expected_action="reset_password")
        if not email:
            raise ValidationException("Invalid or expired password reset token.")

        user = await user_repository.get_by_email(db, email)
        if not user or user.password_reset_token != data["token"]:
            raise ValidationException("Invalid token.")

        # Check token expiration
        if user.password_reset_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise ValidationException("Password reset token has expired.")

        validate_password_strength(data["new_password"])

        # Reset password
        user.hashed_password = password_service.hash_password(data["new_password"])
        user.password_reset_token = None
        user.password_reset_expires_at = None
        # Unlock account if locked
        user.failed_login_attempts = 0
        user.locked_until = None

        db.add(user)

        # Terminate all active sessions
        await session_service.revoke_all_sessions(db, user.id)

        audit = AuditLog(
            user_id=user.id,
            action="user.password_reset_executed",
            resource_type="user",
            resource_id=str(user.id)
        )
        db.add(audit)
        await db.flush()

    async def verify_email(self, db: AsyncSession, token: str) -> None:
        email = password_service.verify_action_token(token, expected_action="verify_email")
        if not email:
            raise ValidationException("Invalid or expired email verification token.")

        user = await user_repository.get_by_email(db, email)
        if not user or user.email_verification_token != token:
            raise ValidationException("Invalid token.")

        if user.email_verification_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise ValidationException("Verification token has expired.")

        user.is_verified = True
        user.email_verification_token = None
        user.email_verification_expires_at = None
        db.add(user)

        audit = AuditLog(
            user_id=user.id,
            action="user.email_verified",
            resource_type="user",
            resource_id=str(user.id)
        )
        db.add(audit)
        await db.flush()

    async def update_profile(self, db: AsyncSession, user_id: uuid.UUID, profile_in: dict) -> User:
        user = await self.get_by_id(db, user_id)

        # Handle unique constraint edits
        if "email" in profile_in and profile_in["email"] != user.email:
            existing = await user_repository.get_by_email(db, profile_in["email"])
            if existing:
                raise ValidationException("Email is already taken.")
            user.email = profile_in["email"]
            user.is_verified = False  # Mark unverified on email change

        if "username" in profile_in and profile_in["username"] != user.username:
            existing = await user_repository.get_by_username(db, profile_in["username"])
            if existing:
                raise ValidationException("Username is already taken.")
            user.username = profile_in["username"]

        if "profile_image_url" in profile_in:
            user.profile_image_url = profile_in["profile_image_url"]

        db.add(user)

        audit = AuditLog(
            user_id=user.id,
            action="user.profile_update",
            resource_type="user",
            resource_id=str(user.id)
        )
        db.add(audit)
        await db.flush()
        return user


user_service = UserService()
