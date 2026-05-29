"""Notification engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_NOTIFICATION,
    PRIORITY_NORMAL,
    PlatformEvent,
)
from backend.centralized_event_bus.service import CentralizedEventBus

logger = logging.getLogger(__name__)


@dataclass
class NotificationEngine:
    """Routes user-facing notifications."""

    settings: AppSettings
    event_bus: CentralizedEventBus | None = None

    def notify(self, message: str) -> None:
        """Log a notification until native notifications are added."""
        logger.info("Notification: %s", message)
        if self.event_bus is not None:
            self.event_bus.publish(
                PlatformEvent(
                    event_type="notification_emitted",
                    source="notification_engine",
                    category=EVENT_CATEGORY_NOTIFICATION,
                    priority=PRIORITY_NORMAL,
                    payload={"message": message},
                )
            )
