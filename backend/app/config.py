"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "PackagePro Estimator"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    postgres_user: str = "ksp"
    postgres_password: str = "ksp"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ksp_estimator"

    @computed_field
    @property
    def database_url(self) -> str:
        """Construct database URL from components."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Authentication
    secret_key: str = "change-me-in-production-use-secrets-gen"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ML Configuration
    ml_min_samples_for_training: int = 50
    ml_confidence_threshold: float = 0.7
    ml_model_path: str = "ml/models"

    # Pricing
    pricing_rules_csv: str = "data/materials/pricing_model.csv"

    # File Storage
    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 10

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    # Companies House API
    companies_house_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
