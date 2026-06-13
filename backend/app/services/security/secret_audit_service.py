import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import SecurityEvent
from app.models.audit import AuditLog


class SecretAuditService:
    async def audit_secret_access(
        self,
        db: AsyncSession,
        key: str,
        accessed_by_id: Optional[uuid.UUID],
        action: str = "ACCESS",  # 'ACCESS', 'DECRYPT', 'EXPOSE'
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log audit entry for secret metadata or key read access."""
        now_status = "SUCCESS" if success else "DENIED"

        # Write to system AuditLog
        audit = AuditLog(
            user_id=accessed_by_id,
            action=f"secret.{action.lower()}",
            resource_type="secret",
            resource_id=key,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"status": now_status, "key": key}
        )
        db.add(audit)

        # High-severity event if unauthorized access/failed access
        severity = "INFO" if success else "HIGH"
        event_type = "SECRET_ACCESS_GRANTED" if success else "SECRET_ACCESS_DENIED"

        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            description=f"Secret access {now_status.lower()} for key '{key}' by user ID {accessed_by_id}",
            user_id=accessed_by_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details_json={"secret_key": key, "action": action, "status": now_status}
        )
        db.add(event)
        await db.flush()


secret_audit_service = SecretAuditService()
