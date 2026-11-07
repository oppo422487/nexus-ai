"""Application configuration for the Nexa AI backend."""

import os

from dotenv import load_dotenv
from pydantic import BaseModel
from app.core.runtime_paths import env_file


class Settings(BaseModel):
    """Runtime settings loaded from environment variables."""

    app_name: str = "Nexa AI Backend"
    app_version: str = "0.1.0"
    app_env: str = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    log_level: str = "INFO"
    sqlite_db_path: str = "backend/data/nexaai.sqlite3"
    enable_voice: bool = False
    enable_web_intelligence: bool = False
    enable_smart_home: bool = False
    enable_dev_tools: bool = True


def _read_bool_env(name: str, default: bool) -> bool:
    """Read a boolean environment variable in a beginner-friendly way."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    """Load environment variables and return application settings."""
    load_dotenv(env_file())

    return Settings(
        app_name=os.getenv("APP_NAME", "Nexa AI Backend"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        app_env=os.getenv("APP_ENV", "development"),
        backend_host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        sqlite_db_path=os.getenv("SQLITE_DB_PATH", "backend/data/nexaai.sqlite3"),
        enable_voice=_read_bool_env("ENABLE_VOICE", False),
        enable_web_intelligence=_read_bool_env("ENABLE_WEB_INTELLIGENCE", False),
        enable_smart_home=_read_bool_env("ENABLE_SMART_HOME", False),
        enable_dev_tools=_read_bool_env("ENABLE_DEV_TOOLS", True),
    )
