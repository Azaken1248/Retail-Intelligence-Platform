import logging
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    databricks_host: str = ""
    databricks_http_path: str = ""
    databricks_token: str = ""

    app_name: str = "Retail Intelligence API"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    gold_schema: str = "raw_data.gold"

    cors_origins: list[str] = ["*"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
