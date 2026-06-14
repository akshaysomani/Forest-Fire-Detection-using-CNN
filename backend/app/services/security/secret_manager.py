import base64
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.security import SecretMetadata, SecretRotationLog, SecurityEvent
from app.core.exceptions import ValidationException


class SecretManager:
    def __init__(self):
        # Derive a valid Fernet key from JWT_SECRET_KEY to avoid initialization crash
        secret_bytes = settings.JWT_SECRET_KEY.encode("utf-8")
        hash_val = hashlib.sha256(secret_bytes).digest()
        self._fernet_key = base64.urlsafe_b64encode(hash_val)
        self._cipher = Fernet(self._fernet_key)

    def encrypt_value(self, raw_value: str) -> str:
        """Encrypt a raw secret string using Fernet symmetric encryption."""
        return self._cipher.encrypt(raw_value.encode("utf-8")).decode("utf-8")

    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a Fernet encrypted string back to raw text."""
        return self._cipher.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")

    async def initialize_and_seed_secrets(self, db: AsyncSession) -> None:
        """Seed metadata for core system credentials if they don't already exist."""
        core_secrets = {
            "JWT_SECRET_KEY": "Symmetric key used to sign and verify JSON Web Tokens.",
            "DATABASE_URL": "Primary PostgreSQL/SQLite connection URI containing credentials.",
            "EXTERNAL_GIS_API_KEY": "Third-party GIS intelligence API authentication token.",
            "AWS_S3_SECRET_ACCESS_KEY": "Cloud storage backend API credentials for dataset archival.",
        }

        now = datetime.utcnow()
        for key, desc in core_secrets.items():
            q = select(SecretMetadata).where(SecretMetadata.key == key)
            res = await db.execute(q)
            if not res.scalar_one_or_none():
                metadata = SecretMetadata(
                    key=key,
                    description=desc,
                    encryption_algorithm="Fernet",
                    last_rotated_at=now,
                    next_rotation_due=now + timedelta(days=90),
                    rotation_interval_days=90,
                    version=1,
                    status="ACTIVE",
                )
                db.add(metadata)
        await db.flush()

    async def get_secret_metadata(self, db: AsyncSession, key: str) -> Optional[SecretMetadata]:
        """Fetch metadata for a given secret key."""
        q = select(SecretMetadata).where(SecretMetadata.key == key, SecretMetadata.status == "ACTIVE")
        res = await db.execute(q)
        return res.scalar_one_or_none()


secret_manager = SecretManager()
