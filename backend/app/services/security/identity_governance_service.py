import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role, user_roles
from app.models.permission import Permission, role_permissions
from app.models.audit import AuditLog
from app.models.security import SecurityEvent
from app.core.exceptions import ValidationException


class IdentityGovernanceService:
    async def create_role(self, db: AsyncSession, name: str, description: Optional[str] = None, current_user_id: Optional[uuid.UUID] = None) -> Role:
        """Create a new security role in the system."""
        # Check if role already exists
        q = select(Role).where(Role.name == name)
        res = await db.execute(q)
        if res.scalar_one_or_none():
            raise ValidationException(f"Role '{name}' already exists.")

        role = Role(name=name, description=description)
        db.add(role)
        await db.flush()

        # Audit
        audit = AuditLog(
            user_id=current_user_id,
            action="role.create",
            resource_type="role",
            resource_id=str(role.id),
            details={"role_name": name, "description": description}
        )
        db.add(audit)

        event = SecurityEvent(
            event_type="IDENTITY_GOVERNANCE_ROLE_CREATED",
            severity="INFO",
            description=f"Security role '{name}' created by user ID {current_user_id}",
            user_id=current_user_id,
            details_json={"role_id": str(role.id), "role_name": name}
        )
        db.add(event)
        return role

    async def delete_role(self, db: AsyncSession, role_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None) -> None:
        """Delete a security role from the system."""
        q = select(Role).where(Role.id == role_id)
        res = await db.execute(q)
        role = res.scalar_one_or_none()
        if not role:
            raise ValidationException("Role not found.")

        # Do not allow deleting Super Admin
        if role.name == "Super Admin":
            raise ValidationException("Cannot delete protected system role: 'Super Admin'")

        # Audit before delete
        audit = AuditLog(
            user_id=current_user_id,
            action="role.delete",
            resource_type="role",
            resource_id=str(role_id),
            details={"role_name": role.name}
        )
        db.add(audit)

        event = SecurityEvent(
            event_type="IDENTITY_GOVERNANCE_ROLE_DELETED",
            severity="WARNING",
            description=f"Security role '{role.name}' deleted by user ID {current_user_id}",
            user_id=current_user_id,
            details_json={"role_id": str(role_id), "role_name": role.name}
        )
        db.add(event)

        # Delete role
        await db.delete(role)
        await db.flush()

    async def assign_role_to_user(self, db: AsyncSession, user_id: uuid.UUID, role_name: str, current_user_id: Optional[uuid.UUID] = None) -> User:
        """Assign a security role to a user."""
        # Get user
        q_user = select(User).where(User.id == user_id, User.deleted_at.is_(None)).options(selectinload(User.roles))
        res_user = await db.execute(q_user)
        user = res_user.scalar_one_or_none()
        if not user:
            raise ValidationException("User not found.")

        # Get role
        q_role = select(Role).where(Role.name == role_name)
        res_role = await db.execute(q_role)
        role = res_role.scalar_one_or_none()
        if not role:
            raise ValidationException(f"Role '{role_name}' not found.")

        # Check if already assigned
        if role in user.roles:
            return user

        # Assign
        user.roles.append(role)
        db.add(user)
        await db.flush()

        # Audit
        audit = AuditLog(
            user_id=current_user_id,
            action="user.role_assign",
            resource_type="user",
            resource_id=str(user_id),
            details={"assigned_role": role_name}
        )
        db.add(audit)

        severity = "HIGH" if role_name in ["Super Admin", "Forest Officer"] else "INFO"
        event = SecurityEvent(
            event_type="IDENTITY_GOVERNANCE_ROLE_ASSIGNED",
            severity=severity,
            description=f"Role '{role_name}' assigned to user {user.username} (ID: {user_id}) by user ID {current_user_id}",
            user_id=current_user_id,
            details_json={"target_user_id": str(user_id), "role_name": role_name}
        )
        db.add(event)
        return user

    async def revoke_role_from_user(self, db: AsyncSession, user_id: uuid.UUID, role_name: str, current_user_id: Optional[uuid.UUID] = None) -> User:
        """Revoke a security role from a user."""
        q_user = select(User).where(User.id == user_id, User.deleted_at.is_(None)).options(selectinload(User.roles))
        res_user = await db.execute(q_user)
        user = res_user.scalar_one_or_none()
        if not user:
            raise ValidationException("User not found.")

        # Prevent removing last Super Admin
        if role_name == "Super Admin":
            # Check how many super admins exist
            q_count = select(User).join(User.roles).where(Role.name == "Super Admin", User.is_active == True, User.deleted_at.is_(None))
            res_count = await db.execute(q_count)
            super_admins = res_count.scalars().all()
            if len(super_admins) <= 1 and any(sa.id == user_id for sa in super_admins):
                raise ValidationException("Cannot revoke role. System must have at least one active Super Admin.")

        # Revoke
        role_to_remove = None
        for role in user.roles:
            if role.name == role_name:
                role_to_remove = role
                break

        if role_to_remove:
            user.roles.remove(role_to_remove)
            db.add(user)
            await db.flush()

            # Audit
            audit = AuditLog(
                user_id=current_user_id,
                action="user.role_revoke",
                resource_type="user",
                resource_id=str(user_id),
                details={"revoked_role": role_name}
            )
            db.add(audit)

            event = SecurityEvent(
                event_type="IDENTITY_GOVERNANCE_ROLE_REVOKED",
                severity="WARNING",
                description=f"Role '{role_name}' revoked from user {user.username} (ID: {user_id}) by user ID {current_user_id}",
                user_id=current_user_id,
                details_json={"target_user_id": str(user_id), "role_name": role_name}
            )
            db.add(event)

        return user

    async def update_role_permissions(self, db: AsyncSession, role_id: uuid.UUID, permission_names: List[str], current_user_id: Optional[uuid.UUID] = None) -> Role:
        """Update the set of permissions assigned to a role."""
        q_role = select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
        res_role = await db.execute(q_role)
        role = res_role.scalar_one_or_none()
        if not role:
            raise ValidationException("Role not found.")

        # Do not allow modifying Super Admin permissions (always has all)
        if role.name == "Super Admin":
            raise ValidationException("Cannot modify permissions of the protected 'Super Admin' role.")

        # Get the permissions objects
        q_perms = select(Permission).where(Permission.name.in_(permission_names))
        res_perms = await db.execute(q_perms)
        perms = res_perms.scalars().all()

        if len(perms) != len(permission_names):
            found_names = {p.name for p in perms}
            missing = set(permission_names) - found_names
            raise ValidationException(f"Invalid permissions provided: {list(missing)}")

        # Update
        old_perms = [p.name for p in role.permissions]
        role.permissions = perms
        db.add(role)
        await db.flush()

        # Audit
        audit = AuditLog(
            user_id=current_user_id,
            action="role.permissions_update",
            resource_type="role",
            resource_id=str(role_id),
            details={"old_permissions": old_perms, "new_permissions": permission_names}
        )
        db.add(audit)

        event = SecurityEvent(
            event_type="IDENTITY_GOVERNANCE_PERMISSIONS_UPDATED",
            severity="HIGH",
            description=f"Permissions for role '{role.name}' updated by user ID {current_user_id}",
            user_id=current_user_id,
            details_json={"role_id": str(role_id), "role_name": role.name, "new_permissions": permission_names}
        )
        db.add(event)
        return role


identity_governance_service = IdentityGovernanceService()
