"""Stable writable paths for development and frozen desktop builds."""

from __future__ import annotations

import os
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    configured = os.getenv("NEXA_DATA_DIR", "").strip()
    path = Path(configured).expanduser() if configured else BACKEND_ROOT / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def models_dir() -> Path:
    configured = os.getenv("NEXA_MODELS_DIR", "").strip()
    path = Path(configured).expanduser() if configured else BACKEND_ROOT / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def env_file() -> Path:
    configured = os.getenv("NEXA_ENV_FILE", "").strip()
    return Path(configured).expanduser().resolve() if configured else BACKEND_ROOT / ".env"
