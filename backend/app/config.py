"""Application settings loaded from environment / .env (pydantic-settings)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://ankur@localhost:5432/conductor"
    sync_database_url: str = "postgresql+psycopg2://ankur@localhost:5432/conductor"

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1/"
    openai_chat_model: str = "gpt-5"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # Google OAuth (web application client)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # App
    frontend_url: str = "http://localhost:5173"
    sync_lookback_days: int = 90
    sync_max_items_per_service: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
