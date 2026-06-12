import uuid
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.core.config import settings
from app.core.exceptions import AuthenticationException, TokenExpiredException


class JWTService:
    @staticmethod
    def create_access_token(user_id: uuid.UUID, email: str, expires_delta: timedelta | None = None) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "exp": expire
        }
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id: uuid.UUID, jti: uuid.UUID, expires_delta: timedelta | None = None) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode = {
            "sub": str(user_id),
            "jti": str(jti),
            "type": "refresh",
            "exp": expire
        }
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str, expected_type: str = "access") -> dict:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )

            token_type = payload.get("type")
            if token_type != expected_type:
                raise AuthenticationException("Invalid token type.")

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredException("Token has expired.")
        except JWTError:
            raise AuthenticationException("Could not validate credentials.")


jwt_service = JWTService()
