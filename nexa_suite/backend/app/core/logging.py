"""Logging utilities for the Nexa AI backend."""

import logging


def setup_logging(log_level: str) -> logging.Logger:
    """Configure and return the main backend logger."""
    logger = logging.getLogger("nexaai.backend")
    logger.setLevel(log_level.upper())

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger
