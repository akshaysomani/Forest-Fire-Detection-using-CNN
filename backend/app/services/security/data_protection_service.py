import hashlib
import os
from typing import Dict, Any
from app.services.security.encryption_manager import encryption_manager
from app.services.security.data_classification_service import data_classification_service


class DataProtectionService:
    def encrypt_data(self, plaintext: str) -> str:
        """Encrypts data using low-level symmetric encryption."""
        return encryption_manager.encrypt(plaintext)

    def decrypt_data(self, ciphertext: str) -> str:
        """Decrypts data using low-level symmetric decryption."""
        return encryption_manager.decrypt(ciphertext)

    def mask_sensitive_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively scans and masks keys containing sensitive identifiers."""
        if not payload:
            return payload

        masked = {}
        for k, v in payload.items():
            if isinstance(v, dict):
                masked[k] = self.mask_sensitive_payload(v)
            elif isinstance(v, list):
                masked_list = []
                for item in v:
                    if isinstance(item, dict):
                        masked_list.append(self.mask_sensitive_payload(item))
                    else:
                        masked_list.append(item)
                masked[k] = masked_list
            else:
                # Classify based on key names
                classification = "INTERNAL"
                # Simple heuristical key classifications
                k_lower = k.lower()
                if any(kw in k_lower for kw in ["password", "token", "secret", "key"]):
                    classification = "RESTRICTED"
                elif any(kw in k_lower for kw in ["email", "phone", "latitude", "longitude", "gps", "coordinate"]):
                    classification = "CONFIDENTIAL"

                if data_classification_service.should_mask(classification):
                    masked[k] = data_classification_service.mask_value(k, str(v))
                else:
                    masked[k] = v
        return masked

    def verify_file_checksum(self, filepath: str, expected_sha256: str) -> bool:
        """Verify the integrity of local files (e.g. model weights) using SHA-256."""
        if not os.path.exists(filepath):
            return False
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest() == expected_sha256

    def generate_file_checksum(self, filepath: str) -> str:
        """Generates a SHA-256 checksum for a local file."""
        if not os.path.exists(filepath):
            return ""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()


data_protection_service = DataProtectionService()
