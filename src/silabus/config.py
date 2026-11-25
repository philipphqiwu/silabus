"""Runtime settings, read from the environment (and `.env` in development)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration in one place so tests can override it via env vars."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://silabus:silabus@localhost:5433/silabus"
    env: str = "dev"

    llm_model: str = ""
    llm_prompt_version: str = "v1"

    http_timeout_seconds: float = 20.0
    http_rate_limit_seconds: float = 2.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
