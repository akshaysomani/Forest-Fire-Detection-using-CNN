import uuid
from typing import AsyncGenerator
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.services.jwt_service import jwt_service
from app.services.permission_service import permission_service

# OAuth2 scheme for token retrieval
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """FastAPI dependency to extract access token and return the current authenticated User."""
    payload = jwt_service.verify_token(token, expected_type="access")
    user_id_str = payload.get("sub")

    if not user_id_str:
        raise AuthenticationException("Token is missing user identifier.")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationException("Invalid user identifier format in token.")

    user = await user_repository.get_user_with_roles_and_permissions(db, user_id)
    if not user:
        raise AuthenticationException("User associated with this token does not exist.")

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency to verify that the current user is active."""
    if not current_user.is_active:
        raise AuthenticationException("User account is deactivated.")
    return current_user


class PermissionChecker:
    """Route guard dependency factory that verifies the active user holds specific permissions."""

    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    async def __call__(
        self, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
    ) -> User:
        has_perm = await permission_service.has_permission(
            db, user_id=current_user.id, required_permission=self.required_permission
        )
        if not has_perm:
            raise AuthorizationException(f"You do not have the required permission: '{self.required_permission}'")
        return current_user
