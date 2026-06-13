import uuid
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.security import SecurityEvent, ComplianceAudit


class PermissionAuditor:
    async def perform_security_audit(self, db: AsyncSession, current_user_id: Optional[uuid.UUID] = None) -> dict:
        """Scan system access records, roles, and user states to identify potential compliance gaps."""
        # 1. Fetch all active users with roles
        q = select(User).where(User.deleted_at.is_(None)).options(selectinload(User.roles).selectinload(Role.permissions))
        res = await db.execute(q)
        users = res.scalars().all()

        orphaned_accounts = []
        excess_privileges = []
        unverified_privileged_users = []

        now_utc = datetime.now(timezone.utc)

        for user in users:
            # Check for Orphaned Accounts (inactive for > 90 days or never logged in and created > 90 days ago)
            last_active = user.last_login_at
            created_at = user.created_at

            # Convert naive datetime from SQLAlchemy to aware in UTC to avoid offset-naive vs offset-aware comparison
            if last_active:
                last_active_aware = last_active.replace(tzinfo=timezone.utc) if last_active.tzinfo is None else last_active
                inactive_days = (now_utc - last_active_aware).days
            else:
                created_at_aware = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
                inactive_days = (now_utc - created_at_aware).days

            if inactive_days > 90 and user.is_active:
                orphaned_accounts.append({
                    "user_id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "inactive_days": inactive_days,
                    "last_login": user.last_login_at.isoformat() if user.last_login_at else None
                })

            # Check for excessive privileges (non-admin, non-officer having > 5 permissions)
            user_roles = [r.name for r in user.roles]
            is_privileged_role = "Super Admin" in user_roles or "Forest Officer" in user_roles

            permissions = set()
            for role in user.roles:
                for perm in role.permissions:
                    permissions.add(perm.name)

            if len(permissions) > 5 and not is_privileged_role:
                excess_privileges.append({
                    "user_id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "roles": user_roles,
                    "permission_count": len(permissions),
                    "permissions": list(permissions)
                })

            # Check for unverified users with privileged roles
            if not user.is_verified and is_privileged_role:
                unverified_privileged_users.append({
                    "user_id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "roles": user_roles
                })

        findings = {
            "orphaned_accounts": orphaned_accounts,
            "excess_privileges": excess_privileges,
            "unverified_privileged_users": unverified_privileged_users,
            "total_issues_found": len(orphaned_accounts) + len(excess_privileges) + len(unverified_privileged_users)
        }

        # Save to ComplianceAudit log
        audit = ComplianceAudit(
            policy_name="IDENTITY_AND_ACCESS_GOVERNANCE_AUDIT",
            checked_by_id=current_user_id,
            status="FAIL" if findings["total_issues_found"] > 0 else "PASS",
            findings=f"Identity access audit found {findings['total_issues_found']} potential issue(s).",
            details_json=findings
        )
        db.add(audit)

        # Trigger security alert if issues > 0
        if findings["total_issues_found"] > 0:
            event = SecurityEvent(
                event_type="ACCESS_GOVERNANCE_VIOLATIONS_DETECTED",
                severity="WARNING" if findings["total_issues_found"] < 5 else "HIGH",
                description=f"Identity and permission audit identified {findings['total_issues_found']} governance discrepancies.",
                user_id=current_user_id,
                details_json={"findings_summary": findings}
            )
            db.add(event)

        return findings


permission_auditor = PermissionAuditor()
