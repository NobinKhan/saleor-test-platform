from __future__ import annotations

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(default="", description="Database connection URL")
    jwt_secret: str = Field(default="CHANGE_ME_IN_PRODUCTION_USE_64CHAR_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    frontend_url: str = "http://localhost:5999"
    app_host: str = "0.0.0.0"
    app_port: int = 5998


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Shared singleton for settings access (avoids repeated function calls)
settings = get_settings()


def get_database_url() -> str:
    """
    Priority:
    1. DATABASE_URL environment variable (set by docker compose)
    2. .env file value
    
    Note: This reads os.environ dynamically at call time, NOT at import time.
    This ensures docker-compose injected env vars are picked up correctly.
    """
    # First check docker-compose injected env var (higher priority)
    docker_url = os.environ.get("DATABASE_URL", "")
    if docker_url:
        return docker_url
    
    # Fall back to .env file / default config value
    config_url = settings.database_url
    if config_url and "localhost:5997" not in config_url:
        return config_url
    
    return ""