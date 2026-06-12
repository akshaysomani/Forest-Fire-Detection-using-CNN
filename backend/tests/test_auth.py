import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.user import User
from app.models.token import RefreshToken
from app.models.session import UserSession
from app.services.password_service import password_service

pytestmark = pytest.mark.asyncio


async def test_register_success(client: AsyncClient, db: AsyncSession):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "officer@forest.org",
            "username": "forest_officer",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "officer@forest.org"
    assert data["username"] == "forest_officer"
    assert "id" in data
    assert data["is_active"] is True
    assert data["is_verified"] is False


async def test_register_duplicate(client: AsyncClient):
    payload = {
        "email": "duplicate@forest.org",
        "username": "duplicate_user",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }
    # First signup
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second signup
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 422
    assert "email" in res2.json()["error"]["message"].lower() or "validation" in res2.json()["error"]["code"].lower() or "already" in res2.json()["error"]["message"].lower()


async def test_login_success(client: AsyncClient):
    # Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@forest.org",
            "username": "login_user",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "login_user",
            "password": "Password123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_failed_attempts_and_lockout(client: AsyncClient, db: AsyncSession):
    email = "locked@forest.org"
    username = "locked_user"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }
    )

    # Tries failed logins 4 times
    for _ in range(4):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": "WrongPassword123!"}
        )
        assert response.status_code == 401

    # Look up user to check attempts
    query = select(User).where(User.username == username)
    res = await db.execute(query)
    user = res.scalar_one()
    assert user.failed_login_attempts == 4

    # 5th attempt locks the account
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "WrongPassword123!"}
    )
    assert response.status_code == 401

    # 6th attempt returns Locked exception
    response2 = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "WrongPassword123!"}
    )
    assert response2.status_code == 403
    assert response2.json()["error"]["code"] == "ACCOUNT_LOCKED"


async def test_token_rotation_and_revocation(client: AsyncClient, db: AsyncSession):
    username = "refresh_user"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@forest.org",
            "username": username,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }
    )

    # Login
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "Password123!"}
    )
    tokens = login_res.json()
    old_refresh = tokens["refresh_token"]

    # Refresh
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh}
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    new_refresh = new_tokens["refresh_token"]
    assert new_refresh != old_refresh

    # Verify old token is revoked in database
    from app.services.token_manager import token_manager
    old_hash = token_manager._hash_token(old_refresh)
    query = select(RefreshToken).where(RefreshToken.token_hash == old_hash)
    res = await db.execute(query)
    old_db_token = res.scalar_one()
    assert old_db_token.is_revoked is True

    # Security check: reuse old token
    reuse_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh}
    )
    assert reuse_res.status_code == 401
    assert "session terminated" in reuse_res.json()["error"]["message"].lower()

    # Verify that the new token is also now revoked due to reuse detection
    new_hash = token_manager._hash_token(new_refresh)
    query2 = select(RefreshToken).where(RefreshToken.token_hash == new_hash)
    res2 = await db.execute(query2)
    new_db_token = res2.scalar_one()
    assert new_db_token.is_revoked is True


async def test_sessions_management(client: AsyncClient):
    username = "session_user"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "session@forest.org",
            "username": username,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }
    )

    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "Password123!"}
    )
    tokens = login_res.json()
    access_token = tokens["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # Fetch active sessions
    sessions_res = await client.get("/api/v1/auth/sessions", headers=headers)
    assert sessions_res.status_code == 200
    sessions = sessions_res.json()
    assert len(sessions) == 1
    session_id = sessions[0]["id"]

    # Delete session (remote logout)
    del_res = await client.delete(f"/api/v1/auth/sessions/{session_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify session list is now empty
    sessions_res_2 = await client.get("/api/v1/auth/sessions", headers=headers)
    assert len(sessions_res_2.json()) == 0


async def test_forgot_and_reset_password_flow(client: AsyncClient, db: AsyncSession):
    email = "forgot@forest.org"
    username = "forgot_user"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "Password123!",
            "confirm_password": "Password123!"
        }
    )

    # Forgot password request
    forgot_res = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 202

    # Extract verification token from database directly
    query = select(User).where(User.email == email)
    res = await db.execute(query)
    user = res.scalar_one()
    reset_token = user.password_reset_token
    assert reset_token is not None

    # Reset password execution
    reset_res = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "NewSecurePassword456!",
            "confirm_new_password": "NewSecurePassword456!"
        }
    )
    assert reset_res.status_code == 204

    # Confirm login succeeds with new password
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "NewSecurePassword456!"}
    )
    assert login_res.status_code == 200
