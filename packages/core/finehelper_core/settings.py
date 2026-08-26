from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_public_url: str = "http://localhost:8000"
    web_origin: str = "http://localhost:3000"
    secret_key: str = "change-me-to-a-long-random-string"
    master_key: str = "change-me-32-byte-key-for-aesgcm!!!!"

    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_db: str = "finehelper"
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
    jwt_ttl_days: int = 7
    gemini_api_key: str | None = None
    # Sarvam AI — India STT/TTS (Hinglish-capable voice shell)
    sarvam_api_key: str | None = None
    sarvam_tts_speaker: str = "anushka"
    trust_model_path: str = "apps/api/finehelper_api/ml/artifacts/trust_model.joblib"
    # Blockchain attestation (optional EVM; local ledger always on)
    chain_rpc_url: str | None = None
    chain_private_key: str | None = None
    chain_contract_address: str | None = None
    chain_id: int = 80002  # Polygon Amoy default
    chain_network: str = "local"
    chain_explorer_url: str = "https://amoy.polygonscan.com"
    # Comma-separated extra CORS origins (in addition to web_origin)
    cors_origins: str = ""
    # Expose OpenAPI docs (disable in production via APP_ENV)
    enable_docs: bool = True

    @property
    def uses_r2(self) -> bool:
        return bool(self.s3_endpoint_url and self.s3_access_key_id and self.s3_secret_access_key)

    @property
    def is_production(self) -> bool:
        return (self.app_env or "").lower() in {"production", "prod", "staging"}

    def allowed_cors_origins(self) -> list[str]:
        origins = {self.web_origin, "http://localhost:3000", "http://127.0.0.1:3000"}
        for part in (self.cors_origins or "").split(","):
            o = part.strip()
            if o:
                origins.add(o)
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    os.makedirs(".data", exist_ok=True)
    return Settings()
