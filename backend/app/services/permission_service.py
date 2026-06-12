import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission


class PermissionService:
    async def get_user_permissions(self, db: AsyncSession, user_id: uuid.UUID) -> set[str]:
        """Aggregate all permissions from all roles assigned to the user."""
        query = select(User).where(User.id == user_id, User.deleted_at.is_(None)).options(
            selectinload(User.roles).selectinload(Role.permissions)
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            return set()

        permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.name)
        return permissions

    async def has_permission(self, db: AsyncSession, user_id: uuid.UUID, required_permission: str) -> bool:
        """Checks if a user has a specific permission."""
        user_permissions = await self.get_user_permissions(db, user_id)
        # Super Admin bypasses all checks
        if "all" in user_permissions or "manage_platform_settings" in user_permissions:
            return True
        return required_permission in user_permissions

    async def seed_roles_and_permissions(self, db: AsyncSession) -> None:
        """Seed the system default roles and permissions."""
        # Define permissions
        permissions_def = {
            "manage_users": "Can create, update, and soft-delete users",
            "manage_roles": "Can manage roles and permissions mapping",
            "upload_images": "Can upload forest fire images for CNN analysis",
            "view_predictions": "Can view CNN inference results",
            "view_reports": "Can generate and view fire logs and metrics",
            "manage_platform_settings": "Can configure site settings and models",
            "access_audit_logs": "Can view system security audit trails",
            "view_alerts": "Can receive emergency active fire alerts",
            "analyze_data": "Can run spatial analytical scripts on fire data"
        }

        db_permissions = {}
        for name, desc in permissions_def.items():
            query = select(Permission).where(Permission.name == name)
            res = await db.execute(query)
            perm = res.scalar_one_or_none()
            if not perm:
                perm = Permission(name=name, description=desc)
                db.add(perm)
            db_permissions[name] = perm

        await db.flush()

        # Define default roles and their mappings
        roles_def = {
            "Super Admin": list(permissions_def.keys()),
            "Forest Officer": ["upload_images", "view_predictions", "view_reports", "view_alerts"],
            "Emergency Response Officer": ["view_predictions", "view_reports", "view_alerts"],
            "Research Analyst": ["view_predictions", "view_reports", "analyze_data"],
            "Viewer": ["view_predictions", "view_reports"]
        }

        for role_name, perm_names in roles_def.items():
            query = select(Role).where(Role.name == role_name).options(selectinload(Role.permissions))
            res = await db.execute(query)
            role = res.scalar_one_or_none()

            if not role:
                role = Role(name=role_name, description=f"Default {role_name} role")
                db.add(role)

            # Assign permissions
            role.permissions = [db_permissions[name] for name in perm_names]
            db.add(role)

        await db.flush()


permission_service = PermissionService()
