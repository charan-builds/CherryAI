"""Reusable observer event bus."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from backend.observer_engine.observer_event_bus.events import ObserverEvent

logger = logging.getLogger(__name__)
ObserverEventHandler = Callable[[ObserverEvent], None]


@dataclass
class ObserverEventBus:
    """Small synchronous event bus for observer components."""

    _subscribers: dict[str, list[ObserverEventHandler]] = field(default_factory=dict)

    def subscribe(self, event_type: str, handler: ObserverEventHandler) -> None:
        """Subscribe a handler to an event type."""
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: ObserverEvent) -> None:
        """Dispatch an event to subscribers."""
        logger.info("Observer event: %s", event.event_type)
        for handler in self._subscribers.get(event.event_type, []):
            try:
                handler(event)
            except Exception:
                logger.exception("Observer event handler failed: %s", event.event_type)
