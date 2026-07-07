"""
Application configuration using pydantic-settings.

All secrets and environment-specific values are loaded from environment
variables or a .env file. This keeps credentials out of source control
and allows seamless switching between local, staging, and production.
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized application settings with validation."""

    # ── Databricks Connection ────────────────────────────────────────
    databricks_host: str = ""
    databricks_http_path: str = ""
    databricks_token: str = ""

    # ── Application ──────────────────────────────────────────────────
    app_name: str = "Retail Intelligence API"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── Data Layer ───────────────────────────────────────────────────
    gold_schema: str = "raw_data.gold"

    # ── CORS ─────────────────────────────────────────────────────────
    cors_origins: list[str] = ["*"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the entire application."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s │ %(name)-30s │ %(levelname)-8s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
