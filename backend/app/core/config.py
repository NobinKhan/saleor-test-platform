from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="development", validation_alias="APP_ENV")
    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    jwt_secret: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_USE_64CHAR_SECRET",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60, validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        default=7, validation_alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )
    frontend_url: str = Field(default="http://localhost:5999", validation_alias="FRONTEND_URL")
    app_host: str = Field(default="0.0.0.0", validation_alias="APP_HOST")
    app_port: int = Field(default=5998, validation_alias="APP_PORT")
    token_encryption_key: str = Field(default="", validation_alias="TOKEN_ENCRYPTION_KEY")
    reference_saleor_url: str = Field(default="", validation_alias="REFERENCE_SALEOR_URL")
    reference_baseline_version: str = Field(
        default="3.23.6",
        validation_alias="REFERENCE_BASELINE_VERSION",
    )
    golden_corpus_version: str = Field(
        default="3.23.7",
        validation_alias="GOLDEN_CORPUS_VERSION",
    )
    reference_baseline_source: str = Field(
        default="saleor-dashboard",
        validation_alias="REFERENCE_BASELINE_SOURCE",
    )
    saleor_graphql_url_default: str = Field(
        default="http://saleor-api:8000/graphql/",
        validation_alias="SALEOR_GRAPHQL_URL",
    )
    allow_insecure_jwt_secret: bool = Field(default=True, validation_alias="ALLOW_INSECURE_JWT_SECRET")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def get_database_url() -> str:
    docker_url = os.environ.get("DATABASE_URL", "")
    if docker_url:
        return docker_url
    config_url = settings.database_url
    if config_url and "localhost:5997" not in config_url:
        return config_url
    return ""
