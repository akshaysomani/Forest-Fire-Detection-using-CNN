import uuid
from typing import List
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_active_user, PermissionChecker
from app.core.exceptions import ValidationException
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest
)
from app.schemas.token import TokenResponse, TokenRefreshRequest, TokenLogoutRequest
from app.schemas.session import SessionResponse
from app.services.user_service import user_service
from app.services.jwt_service import jwt_service
from app.services.token_manager import token_manager
from app.services.session_service import session_service

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user and issues an email verification token."""
    new_user = await user_service.register_user(db, user_in.model_dump())
    await db.commit()
    from app.repositories.user_repository import user_repository
    refreshed_user = await user_repository.get_user_with_roles_and_permissions(db, new_user.id)
    return refreshed_user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Logs in a user, tracking the active session and device details."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    user = await user_service.authenticate_user(
        db,
        identifier=form_data.username,
        password=form_data.password,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # Generate rotation token pairs
    # Create the refresh token record first (which gives us a unique UUID identifier 'jti')
    # and then create the session and generate the token.
    # We will pass the parent token hash as None for a fresh login.
    refresh_token_str, db_token = await token_manager.create_refresh_token_record(db, user_id=user.id)

    # Save user session
    await session_service.create_session(
        db,
        user_id=user.id,
        refresh_token_id=db_token.id,
        ip_address=ip_address,
        user_agent=user_agent
    )

    access_token_str = jwt_service.create_access_token(user_id=user.id, email=user.email)

    await db.commit()

    return TokenResponse(
        access_token=access_token_str,
        refresh_token=refresh_token_str
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(logout_in: TokenLogoutRequest, db: AsyncSession = Depends(get_db)):
    """Invalidates the refresh token and deactivates the corresponding session."""
    await token_manager.revoke_refresh_token(db, logout_in.refresh_token)
    await db.commit()


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_in: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """Rotates the refresh token and issues a new access/refresh pair (RTR)."""
    access_token, refresh_token = await token_manager.rotate_refresh_token(
        db,
        refresh_in.refresh_token
    )
    await db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(forgot_in: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Initiates password reset request and generates a temporary reset token."""
    await user_service.initiate_password_reset(db, forgot_in.email)
    await db.commit()
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(reset_in: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Resets the user password using a verified token and terminates all active sessions."""
    await user_service.execute_password_reset(db, reset_in.model_dump())
    await db.commit()


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(verify_in: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Verifies a user's email using a signed verification token."""
    await user_service.verify_email(db, verify_in.token)
    await db.commit()


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """Retrieves the profile of the current authenticated user."""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates selected user profile details."""
    updated_user = await user_service.update_profile(
        db,
        user_id=current_user.id,
        profile_in=profile_in.model_dump(exclude_unset=True)
    )
    await db.commit()
    from app.repositories.user_repository import user_repository
    refreshed_user = await user_repository.get_user_with_roles_and_permissions(db, updated_user.id)
    return refreshed_user


@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_in: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates the user password and terminates all active sessions for security."""
    await user_service.change_password(
        db,
        user_id=current_user.id,
        data=password_in.model_dump()
    )
    await db.commit()


@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns a list of all active sessions and devices for the authenticated user."""
    return await session_service.get_active_sessions(db, current_user.id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivates a specific session, forcing logout on that device."""
    revoked = await session_service.revoke_session(db, session_id, current_user.id)
    if not revoked:
        raise ValidationException("Session could not be found or is already inactive.")
    await db.commit()
