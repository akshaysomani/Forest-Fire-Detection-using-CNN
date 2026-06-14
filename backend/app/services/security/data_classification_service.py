from typing import Dict, Set


class DataClassificationService:
    def __init__(self):
        # Map fields to their respective classification tiers: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
        self._classifications: Dict[str, Dict[str, str]] = {
            "user": {
                "id": "INTERNAL",
                "username": "INTERNAL",
                "email": "CONFIDENTIAL",
                "hashed_password": "RESTRICTED",
                "profile_image_url": "CONFIDENTIAL",
                "last_login_at": "INTERNAL",
            },
            "incident": {
                "id": "INTERNAL",
                "title": "INTERNAL",
                "description": "INTERNAL",
                "status": "INTERNAL",
                "severity": "INTERNAL",
            },
            "gis": {
                "id": "INTERNAL",
                "latitude": "CONFIDENTIAL",
                "longitude": "CONFIDENTIAL",
                "address": "CONFIDENTIAL",
                "elevation": "INTERNAL",
            },
            "secret": {"key": "RESTRICTED", "value": "RESTRICTED"},
            "alert": {
                "id": "INTERNAL",
                "message": "INTERNAL",
                "recipient_phone": "CONFIDENTIAL",
                "recipient_email": "CONFIDENTIAL",
            },
        }

    def get_field_classification(self, table: str, field: str) -> str:
        """Returns the classification tier of a specific table column."""
        tbl = table.lower()
        fld = field.lower()
        if tbl in self._classifications and fld in self._classifications[tbl]:
            return self._classifications[tbl][fld]
        return "INTERNAL"  # Default fallback tier

    def should_mask(self, classification: str) -> bool:
        """Indicates if values in this tier should be masked during standard telemetry outputs."""
        return classification in ["CONFIDENTIAL", "RESTRICTED"]

    def mask_value(self, field_name: str, value: str) -> str:
        """Masks sensitive values (e.g. user emails, phone numbers, coordinates)."""
        if not value:
            return ""
        val_str = str(value)
        if "email" in field_name.lower():
            if "@" in val_str:
                parts = val_str.split("@")
                masked_name = parts[0][0] + "***" if len(parts[0]) > 1 else "*"
                return f"{masked_name}@{parts[1]}"
            return "***@***"
        elif "phone" in field_name.lower():
            return val_str[:3] + "****" + val_str[-3:] if len(val_str) > 6 else "****"
        elif field_name.lower() in ["latitude", "longitude"]:
            return "**.****"
        return "********"


data_classification_service = DataClassificationService()
