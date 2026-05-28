"""Notification engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings

logger = logging.getLogger(__name__)


@dataclass
class NotificationEngine:
    """Routes user-facing notifications."""

    settings: AppSettings

    def notify(self, message: str) -> None:
        """Log a notification until native notifications are added."""
        logger.info("Notification: %s", message)
