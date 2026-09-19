from functools import lru_cache
from typing import Optional
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

    # AI / Cloud Provider Keys & Automatic Fallback
    AI_FALLBACK_ENABLED: bool = True
    PROVIDER_COOLDOWN_SECONDS: int = 60
    OCR_PROVIDER: str = "gemini"  # Primary default ("gemini" | "groq")
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_MODELS: str = "gemini-3.6-flash,gemini-3.8-flash,gemini-3.7-flash,gemini-3.5-flash"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_MODELS: str = "qwen/qwen3.8-27b"

    def get_gemini_models(self) -> list[str]:
        """Return ordered list of Gemini vision models, preferring GEMINI_MODEL if configured."""
        models: list[str] = []
        if self.GEMINI_MODEL:
            models.append(self.GEMINI_MODEL.strip())
        if self.GEMINI_MODELS:
            for item in self.GEMINI_MODELS.split(","):
                m = item.strip()
                if m and m not in models:
                    models.append(m)
        return models or ["gemini-3.6-flash"]

    def get_groq_models(self) -> list[str]:
        """Return ordered list of Groq vision models, preferring GROQ_MODEL if configured."""
        models: list[str] = []
        if self.GROQ_MODEL:
            models.append(self.GROQ_MODEL.strip())
        if self.GROQ_MODELS:
            for item in self.GROQ_MODELS.split(","):
                m = item.strip()
                if m and m not in models:
                    models.append(m)
        return models or ["qwen/qwen3.8-27b"]

    # GTIN Product Identity Provider Configuration (Phase 2 & 2B & Controlled Prototype)
    GTIN_PROVIDER: str = "LOCAL_CATALOG"  # "LOCAL_CATALOG" | "OPEN_FOOD_FACTS" | "LOCAL_FIXTURE"
    LOCAL_CATALOG_PATH: str = "backend/data/products.json"
    OFF_API_BASE_URL: str = "https://world.openfoodfacts.org"
    OFF_TIMEOUT_SECONDS: float = 3.0
    OFF_USER_AGENT: str = "PackCheck - Web - Version 0.1.0 - https://github.com/packcheck"

    # Logging Configuration
    LOG_DIR: str = "logs"
    LOG_FILE: str = "packcheck.log"
    LOG_MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
    LOG_BACKUP_COUNT: int = 3
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton factory."""
    return Settings()
