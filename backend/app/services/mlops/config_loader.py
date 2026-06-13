import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("mlops.config_loader")


class ConfigLoader:
    @staticmethod
    def load_from_environment() -> Dict[str, Any]:
        """Loads all standard application configurations from local environment variables."""
        return {
            "database_url": os.getenv("DATABASE_URL", "sqlite+aiosqlite:///app.db"),
            "storage_provider": os.getenv("STORAGE_PROVIDER", "local"),
            "storage_base_dir": os.getenv("STORAGE_BASE_DIR", "storage"),
            "jwt_secret_key": os.getenv("JWT_SECRET_KEY", "supersecretkey"),
            "port": int(os.getenv("PORT", "8000")),
        }

    @staticmethod
    def decrypt_value(value: str) -> str:
        """
        Mocks a decryption provider (e.g., AWS KMS or HashiCorp Vault)
        for credentials starting with 'vault::'.
        """
        if value.startswith("vault::"):
            # Mock secure vault parsing: strip prefix and reverse string as a mock decryption
            encrypted_payload = value[len("vault::"):]
            decrypted = encrypted_payload[::-1]
            logger.info("Successfully decrypted secret value from Vault provider.")
            return decrypted
        return value

    @staticmethod
    def decrypt_dict_secrets(data: Dict[str, Any]) -> Dict[str, Any]:
        """Iterates over a dictionary and decrypts any values containing secret tokens."""
        decrypted = {}
        for k, v in data.items():
            if isinstance(v, str):
                decrypted[k] = ConfigLoader.decrypt_value(v)
            elif isinstance(v, dict):
                decrypted[k] = ConfigLoader.decrypt_dict_secrets(v)
            else:
                decrypted[k] = v
        return decrypted


config_loader = ConfigLoader()
