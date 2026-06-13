import logging
from typing import Dict, Any, Optional, Tuple
from app.core.exceptions import ValidationException
from app.services.mlops.config_loader import config_loader

logger = logging.getLogger("mlops.environment_manager")


class EnvironmentManager:
    @staticmethod
    def validate_configuration(
        config_data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates the configuration parameters against a schema format.
        If no schema is provided, checks for standard expected variables.
        """
        if not schema:
            # Standard baseline checks
            required_keys = {"database_url", "storage_provider", "storage_base_dir"}
            missing = required_keys - set(config_data.keys())
            if missing:
                return False, f"Missing required configuration properties: {list(missing)}"
            return True, None

        # Custom JSON schema verification
        for key, expected_type in schema.items():
            if key not in config_data:
                return False, f"Missing expected key '{key}' from configuration profile."
            
            val = config_data[key]
            if expected_type == "int":
                try:
                    int(val)
                except ValueError:
                    return False, f"Configuration key '{key}' expects an integer, got '{val}'."
            elif expected_type == "str" and not isinstance(val, str):
                return False, f"Configuration key '{key}' expects a string, got type '{type(val).__name__}'."
            elif expected_type == "dict" and not isinstance(val, dict):
                return False, f"Configuration key '{key}' expects a dictionary, got type '{type(val).__name__}'."

        return True, None

    @staticmethod
    def load_active_config(
        raw_config: Dict[str, Any],
        decrypt_secrets: bool = True
    ) -> Dict[str, Any]:
        """Resolves configuration variables and handles secure vault mock decryption."""
        if decrypt_secrets:
            return config_loader.decrypt_dict_secrets(raw_config)
        return raw_config


environment_manager = EnvironmentManager()
