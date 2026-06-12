import pytest
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.services.permission_service import permission_service
from app.api.deps import PermissionChecker
from app.core.exceptions import AuthorizationException

pytestmark = pytest.mark.asyncio


async def test_role_seeding_and_hierarchy(db: AsyncSession):
    # Verify Super Admin has all permissions
    query = select(Role).where(Role.name == "Super Admin").options(selectinload(Role.permissions))
    res = await db.execute(query)
    super_admin = res.scalar_one()
    
    permissions = {p.name for p in super_admin.permissions}
    assert "manage_users" in permissions
    assert "view_predictions" in permissions
    assert "access_audit_logs" in permissions

    # Verify Viewer has restricted permissions
    query_viewer = select(Role).where(Role.name == "Viewer").options(selectinload(Role.permissions))
    res_viewer = await db.execute(query_viewer)
    viewer = res_viewer.scalar_one()
    
    viewer_perms = {p.name for p in viewer.permissions}
    assert "view_predictions" in viewer_perms
    assert "view_reports" in viewer_perms
    assert "manage_users" not in viewer_perms


async def test_permission_checker_dependency_pass(db: AsyncSession):
    # Setup test user with Viewer role
    query = select(Role).where(Role.name == "Viewer")
    res = await db.execute(query)
    viewer_role = res.scalar_one()

    user = User(
        email="viewer@forest.org",
        username="viewer_user",
        hashed_password="hashedpassword",
        is_active=True,
        is_verified=True
    )
    user.roles.append(viewer_role)
    db.add(user)
    await db.flush()

    # Verify checking permission Viewer has
    checker = PermissionChecker("view_predictions")
    # Should run without raising exceptions
    checked_user = await checker(current_user=user, db=db)
    assert checked_user == user


async def test_permission_checker_dependency_fail(db: AsyncSession):
    # Setup test user with Viewer role
    query = select(Role).where(Role.name == "Viewer")
    res = await db.execute(query)
    viewer_role = res.scalar_one()

    user = User(
        email="viewer_fail@forest.org",
        username="viewer_fail_user",
        hashed_password="hashedpassword",
        is_active=True,
        is_verified=True
    )
    user.roles.append(viewer_role)
    db.add(user)
    await db.flush()

    # Verify checking permission Viewer does NOT have
    checker = PermissionChecker("manage_users")
    
    with pytest.raises(AuthorizationException) as exc_info:
        await checker(current_user=user, db=db)
    
    assert "required permission" in str(exc_info.value)
