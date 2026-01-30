"""
Configuration management using Pydantic Settings.

Environment variables are loaded with sensible defaults for development.
For production, set DATABASE_URL and REDIS_URL explicitly.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ClawBot Coordinator"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = Field(default=False, description="Enable debug mode")

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://clawbot:clawbot@localhost:5432/clawbot_coordinator",
        description="Async PostgreSQL connection string",
    )
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=50)

    # Redis
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for caching and pub/sub",
    )
    redis_max_connections: int = Field(default=10, ge=1, le=100)

    # API Server
    api_host: str = Field(default="0.0.0.0", description="API server bind address")
    api_port: int = Field(default=8000, ge=1024, le=65535)
    api_workers: int = Field(default=1, ge=1, le=16)

    # WebSocket
    ws_heartbeat_interval: int = Field(
        default=30,
        ge=5,
        le=300,
        description="WebSocket heartbeat interval in seconds",
    )
    ws_timeout: int = Field(
        default=90,
        ge=10,
        le=600,
        description="WebSocket connection timeout in seconds",
    )

    # Task Management
    task_default_timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Default task timeout in seconds",
    )
    task_retry_max_attempts: int = Field(default=3, ge=1, le=10)

    # Security
    jwt_secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_minutes: int = Field(default=60, ge=5, le=43200)

    # Monitoring
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    enable_metrics: bool = Field(default=False, description="Enable Prometheus metrics")


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once during application lifetime.
    """
    return Settings()


# Global settings instance for convenience
settings = get_settings()
