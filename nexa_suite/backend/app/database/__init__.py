"""Database package for the Nexa AI backend."""

from .local_config import LocalDatabaseConfig
from .local_config import get_local_database_config

__all__ = [
    "LocalDatabaseConfig",
    "get_local_database_config",
]
