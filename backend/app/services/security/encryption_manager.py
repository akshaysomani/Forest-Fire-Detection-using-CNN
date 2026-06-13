import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


class EncryptionManager:
    def __init__(self):
        # Derive key using SHA-256 for data protection
        derived = hashlib.sha256(f"{settings.JWT_SECRET_KEY}_dataprotect".encode("utf-8")).digest()
        self._key = base64.urlsafe_b64encode(derived)
        self._fernet = Fernet(self._key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypts plain text string into Fernet cipher text."""
        if not plaintext:
            return plaintext
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts Fernet cipher text back to plain text."""
        if not ciphertext:
            return ciphertext
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except Exception:
            # Fallback to returning original cipher if not encrypted
            return ciphertext


encryption_manager = EncryptionManager()
