import os
from typing import List, Union
from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Forest Fire Detection API"
    API_V1_STR: str = "/api/v1"

    # Security Config
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database Config
    DATABASE_URL: str

    # Storage Config
    STORAGE_PROVIDER: str = "local"
    STORAGE_BASE_DIR: str = "./storage"
    AWS_S3_BUCKET: str = "forest-fire-detection-datasets"
    GCS_BUCKET: str = "forest-fire-detection-datasets"
    AZURE_CONTAINER: str = "forest-fire-detection-datasets"

    # Default Super Admin Seed data
    DEFAULT_ADMIN_EMAIL: EmailStr = "admin@forestfire.org"
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "SuperSecurePassword123!"

    # CORS settings
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        return []


settings = Settings()
