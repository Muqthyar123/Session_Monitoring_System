import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "College Faculty Attendance & Session Monitoring System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Require an explicit connection string so the application never silently
    # falls back to a local MongoDB instance.
    MONGODB_URI: str
    DATABASE_NAME: str
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 3000  # 3 seconds — fail fast if Atlas unreachable
    MAX_UPLOAD_SIZE_MB: int = Field(default=20, ge=1, le=100)
    MAX_IMPORT_ROWS: int = Field(default=10000, ge=1, le=100000)

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    FRONTEND_URL: str = "http://localhost:5173"
    TIMEZONE: str = "Asia/Kolkata"

    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None
    FIREBASE_CLIENT_EMAIL: Optional[str] = None

    model_config = SettingsConfigDict(
        # The repository-root .env is the single local source of MongoDB
        # credentials, regardless of the process working directory.
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("MONGODB_URI")
    @classmethod
    def validate_mongodb_uri(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("MONGODB_URI must use mongodb:// or mongodb+srv://")
        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname
            username = parsed.username
            password = parsed.password
        except ValueError:
            raise ValueError("MONGODB_URI is malformed") from None
        if not hostname or not username or password is None:
            raise ValueError("MONGODB_URI must include a host and database-user credentials")

        raw_userinfo = parsed.netloc.rsplit("@", 1)[0]
        raw_username, separator, raw_password = raw_userinfo.partition(":")
        if not separator:
            raise ValueError("MONGODB_URI must include a username and password")
        for component in (raw_username, raw_password):
            if re.search(r"%(?![0-9A-Fa-f]{2})", component):
                raise ValueError("MONGODB_URI credentials contain malformed percent-encoding")
        if any(char in raw_username for char in ":/?#[]@") or any(
            char in raw_password for char in ":/?#[]@"
        ):
            raise ValueError("Reserved characters in MONGODB_URI credentials must be percent-encoded")
        return value

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return value

    def get_database_name(self) -> str:
        return self.DATABASE_NAME


settings = Settings()

