import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "College Faculty Attendance & Session Monitoring System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = Field(default="college_session_monitoring", validation_alias="DATABASE_NAME")
    MONGODB_DATABASE: Optional[str] = Field(default=None, validation_alias="MONGODB_DATABASE")
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 3000  # 3 seconds — fail fast if Atlas unreachable

    JWT_SECRET_KEY: str = "supersecretkey_change_in_production_1234567890"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    FRONTEND_URL: str = "http://localhost:5173"
    TIMEZONE: str = "Asia/Kolkata"

    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None
    FIREBASE_CLIENT_EMAIL: Optional[str] = None

    DATA_DIR: str = str(BASE_DIR / "data")
    DB_STORE_FILE: str = str(BASE_DIR / "data" / "db_store.json")
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "uploads")

    model_config = SettingsConfigDict(
        env_file=(".env", str(BASE_DIR / ".env"), str(BASE_DIR.parent / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_database_name(self) -> str:
        return self.MONGODB_DATABASE or self.DATABASE_NAME


settings = Settings()

