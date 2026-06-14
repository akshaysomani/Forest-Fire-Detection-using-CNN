import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import SecretMetadata, SecretRotationLog, SecurityEvent
from app.services.security.secret_manager import secret_manager
from app.core.exceptions import ValidationException


class CredentialRotationService:
    async def rotate_secret(self, db: AsyncSession, key: str, rotated_by_id: Optional[uuid.UUID] = None) -> SecretMetadata:
        """Executes a credential rotation workflow for the specified key."""
        q = select(SecretMetadata).where(SecretMetadata.key == key)
        res = await db.execute(q)
        secret = res.scalar_one_or_none()

        if not secret:
            raise ValidationException(f"Secret metadata for key '{key}' does not exist.")

        now = datetime.utcnow()
        try:
            # Under a real setup, we would update external vault credentials.
            # Here we update version, timestamp, and schedule next rotation.
            secret.version += 1
            secret.last_rotated_at = now
            secret.next_rotation_due = now + timedelta(days=secret.rotation_interval_days)
            db.add(secret)

            # Log success
            log = SecretRotationLog(secret_key=key, rotated_at=now, rotated_by_id=rotated_by_id, status="SUCCESS")
            db.add(log)

            event = SecurityEvent(
                event_type="SECRET_ROTATED",
                severity="HIGH",
                description=f"Secret credentials for key '{key}' successfully rotated (Version: {secret.version})",
                user_id=rotated_by_id,
                details_json={"secret_key": key, "new_version": secret.version},
            )
            db.add(event)

            await db.flush()
            return secret

        except Exception as e:
            # Log failure
            log = SecretRotationLog(
                secret_key=key, rotated_at=now, rotated_by_id=rotated_by_id, status="FAILURE", error_message=str(e)
            )
            db.add(log)

            event = SecurityEvent(
                event_type="SECRET_ROTATION_FAILED",
                severity="CRITICAL",
                description=f"Automated rotation for secret key '{key}' failed: {str(e)}",
                user_id=rotated_by_id,
                details_json={"secret_key": key, "error": str(e)},
            )
            db.add(event)
            await db.flush()
            raise ValidationException(f"Failed to rotate secret '{key}': {str(e)}")


credential_rotation_service = CredentialRotationService()
