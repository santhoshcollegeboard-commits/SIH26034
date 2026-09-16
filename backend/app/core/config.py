from functools import lru_cache
from typing import Optional
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    APP_NAME: str = "PackCheck"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"

    # SQLite Evidence Ledger database path
    SQLITE_DB_PATH: str = "data/packcheck.db"

    # AI / Cloud Provider Keys (Phase 1 Prototyping)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-flash-latest"
    GROQ_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton factory."""
    return Settings()
