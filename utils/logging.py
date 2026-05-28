"""Logging configuration for Cherry AI."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config.settings import AppSettings


def configure_logging(settings: AppSettings) -> None:
    """Configure console and rotating file logging.

    The root logger is configured once at startup so every module can simply
    call logging.getLogger(__name__) and inherit the same behavior.
    """
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.logs_dir / "cherry_ai.log"

    level = getattr(logging, settings.log_level, logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
