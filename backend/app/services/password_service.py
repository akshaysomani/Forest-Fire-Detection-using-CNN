from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def generate_action_token(email: str, action: str, expires_in_minutes: int = 60) -> str:
        """Generates a secure, signed JWT action token (for email verification or password resets)."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        payload = {"sub": email, "action": action, "exp": expire}
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def verify_action_token(token: str, expected_action: str) -> str | None:
        """Verifies the action token and returns the email (subject) if valid, else None."""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("action") != expected_action:
                return None
            return payload.get("sub")
        except JWTError:
            return None


password_service = PasswordService()
