"""
Application Configuration
Centralized settings management using Pydantic BaseSettings.
All values can be overridden via environment variables or .env file.
"""

import secrets
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Bengali PDF Search System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(32)
    API_PREFIX: str = "/api"

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./bengali_pdf_search.db"
    # For PostgreSQL: postgresql+asyncpg://user:password@localhost:5432/dbname
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # ─── JWT Auth ─────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ─── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # ─── File Storage ─────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    EXPORT_DIR: str = "./exports"
    LOG_DIR: str = "./logs"
    MAX_UPLOAD_SIZE_MB: int = 500  # 500MB per file
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]

    # ─── Processing ───────────────────────────────────────────────────────────
    MAX_WORKERS: int = 4               # Thread pool workers for PDF processing
    OCR_CONFIDENCE_THRESHOLD: float = 0.6
    BATCH_SIZE: int = 10               # PDFs to process per batch
    PDF_DPI: int = 300                 # DPI for image conversion

    # ─── Redis (optional, for queue/cache) ────────────────────────────────────
    REDIS_URL: Optional[str] = None
    CACHE_TTL_SECONDS: int = 300       # 5 minutes

    # ─── Search ───────────────────────────────────────────────────────────────
    SEARCH_RESULTS_LIMIT: int = 100
    SEARCH_DEBOUNCE_MS: int = 300

    # ─── OCR ──────────────────────────────────────────────────────────────────
    TESSERACT_CMD: str = "tesseract"
    EASYOCR_GPU: bool = False          # Set True if GPU available
    OCR_LANGUAGES: List[str] = ["ben", "eng"]  # Bengali + English

    # ─── Security ─────────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_LOGIN_ATTEMPTS: int = 5
    BCRYPT_ROUNDS: int = 12

    @property
    def upload_path(self) -> Path:
        return Path(self.UPLOAD_DIR)

    @property
    def export_path(self) -> Path:
        return Path(self.EXPORT_DIR)

    @property
    def is_postgresql(self) -> bool:
        return "postgresql" in self.DATABASE_URL

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
