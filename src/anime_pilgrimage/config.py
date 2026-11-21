"""Application configuration powered by Pydantic Settings."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path:
    """Locate repository root when running from a subdirectory (editable install)."""
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").is_file() or (cwd / ".env").is_file():
        return cwd
    # src/anime_pilgrimage/config.py -> parents[2] is repo root
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "pyproject.toml").is_file():
        return candidate
    return cwd


def _default_env_files() -> tuple[str, ...]:
    root = _find_project_root()
    cwd_env = Path.cwd() / ".env"
    root_env = root / ".env"
    if cwd_env.resolve() == root_env.resolve():
        return (str(root_env),)
    # Later files take precedence in pydantic-settings
    return (str(root_env), str(cwd_env))


class Settings(BaseSettings):
    """Typed runtime settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=_default_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenRouter LLM/VLM settings
    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    openrouter_llm_model: str = Field(default="openrouter/free")
    openrouter_vlm_model: str = Field(default="openrouter/free")
    openrouter_fallback_models: str = Field(default="")
    openrouter_site_url: str = Field(
        default="https://github.com/TheMattBin/AnimePilgrimageTripPlanner"
    )
    openrouter_app_name: str = Field(default="Anime Pilgrimage Trip Planner")
    openrouter_timeout_seconds: float = Field(default=60.0)
    openrouter_max_retries: int = Field(default=3)

    # Search settings
    tavily_api_key: str = Field(default="")

    # Geocoding (Nominatim) settings
    nominatim_user_agent: str = Field(default="AnimePilgrimageTripPlanner/0.2")
    nominatim_email: str = Field(default="")

    # Crawler settings
    crawler_max_iterations: int = Field(default=2)
    crawler_max_pages: int = Field(default=8)
    crawler_max_concurrency: int = Field(default=4)
    crawler_request_timeout: float = Field(default=15.0)
    crawler_min_locations: int = Field(default=4)

    # Cache & logging
    cache_dir: Path | None = Field(default=None)
    log_level: str = Field(default="INFO")

    @field_validator("cache_dir", mode="before")
    @classmethod
    def _empty_cache_dir_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def has_openrouter_key(self) -> bool:
        key = self.openrouter_api_key.strip()
        return bool(key) and key != "your_openrouter_api_key_here"

    @property
    def fallback_models(self) -> list[str]:
        if not self.openrouter_fallback_models.strip():
            return []
        return [
            model.strip()
            for model in self.openrouter_fallback_models.split(",")
            if model.strip()
        ]

    @property
    def resolved_cache_dir(self) -> Path:
        if self.cache_dir is not None and str(self.cache_dir).strip():
            return self.cache_dir
        return _find_project_root() / ".cache"

    @property
    def cache_db_path(self) -> Path:
        return self.resolved_cache_dir / "cache.sqlite3"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once for CLI or library usage."""
    resolved_level = (level or get_settings().log_level).upper()
    logging.basicConfig(
        level=getattr(logging, resolved_level, logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
