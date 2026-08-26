from __future__ import annotations

import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_public_url: str = "http://localhost:8000"
    web_origin: str = "http://localhost:3000"
    secret_key: str = "change-me-to-a-long-random-string"
    master_key: str = "change-me-32-byte-key-for-aesgcm!!!!"

    database_url: str = "sqlite+aiosqlite:///./.data/finehelper.db"
    redis_url: str | None = None

    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket: str = "finehelper"
    s3_region: str = "auto"

    local_storage_dir: str = ".data/storage"
    fh_embedded_worker: bool = True

    modal_token_id: str | None = None
    modal_token_secret: str | None = None
    hf_token: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def _norm_db(cls, value: object) -> str:
        return _normalize_database_url(str(value))

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def uses_r2(self) -> bool:
        return bool(self.s3_endpoint_url and self.s3_access_key_id and self.s3_secret_access_key)


@lru_cache
def get_settings() -> Settings:
    os.makedirs(".data", exist_ok=True)
    return Settings()
