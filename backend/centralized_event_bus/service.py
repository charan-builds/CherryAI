"""Centralized publish-subscribe event bus."""

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from backend.centralized_event_bus.schemas import (
    EventBusMetrics,
    EventFilter,
    PlatformEvent,
)

logger = logging.getLogger(__name__)

EventHandler = Callable[[PlatformEvent], object]
EventMiddleware = Callable[[PlatformEvent], PlatformEvent | None]


@dataclass
class EventSubscription:
    """One event bus subscription."""

    handler: EventHandler
    event_filter: EventFilter
    name: str = ""


@dataclass
class CentralizedEventBus:
    """Thread-safe event dispatcher for runtime-wide platform events."""

    history_limit: int = 500
    subscriptions: list[EventSubscription] = field(default_factory=list)
    middleware: list[EventMiddleware] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._history: deque[PlatformEvent] = deque(maxlen=self.history_limit)
        self._lock = threading.RLock()
        self._published_count = 0
        self._delivered_count = 0
        self._dropped_count = 0

    def subscribe(
        self,
        handler: EventHandler,
        event_filter: EventFilter | None = None,
        name: str = "",
    ) -> None:
        """Register an event handler."""
        subscription = EventSubscription(
            handler=handler,
            event_filter=event_filter or EventFilter(),
            name=name,
        )
        with self._lock:
            self.subscriptions.append(subscription)

    def add_middleware(self, middleware: EventMiddleware) -> None:
        """Register middleware that can enrich or drop events."""
        with self._lock:
            self.middleware.append(middleware)

    def publish(self, event: PlatformEvent) -> PlatformEvent | None:
        """Publish an event synchronously."""
        processed = self._apply_middleware(event)
        if processed is None:
            with self._lock:
                self._dropped_count += 1
            return None

        with self._lock:
            self._published_count += 1
            self._history.append(processed)
            subscriptions = list(self.subscriptions)

        logger.info(
            "event=%s category=%s source=%s trace_id=%s priority=%s",
            processed.event_type,
            processed.category,
            processed.source,
            processed.trace_id,
            processed.priority,
        )

        for subscription in subscriptions:
            if not subscription.event_filter.matches(processed):
                continue
            self._deliver(subscription, processed)

        return processed

    async def publish_async(self, event: PlatformEvent) -> PlatformEvent | None:
        """Async-ready publish wrapper."""
        return await asyncio.to_thread(self.publish, event)

    def recent_events(self, limit: int = 50) -> list[PlatformEvent]:
        """Return recent events newest-first."""
        with self._lock:
            return list(reversed(list(self._history)[-limit:]))

    def metrics(self) -> EventBusMetrics:
        """Return current event bus counters."""
        with self._lock:
            return EventBusMetrics(
                published_count=self._published_count,
                delivered_count=self._delivered_count,
                dropped_count=self._dropped_count,
                subscriber_count=len(self.subscriptions),
                history_size=len(self._history),
            )

    def _apply_middleware(self, event: PlatformEvent) -> PlatformEvent | None:
        processed: PlatformEvent | None = event
        with self._lock:
            middleware = list(self.middleware)
        for handler in middleware:
            if processed is None:
                return None
            processed = handler(processed)
        return processed

    def _deliver(
        self,
        subscription: EventSubscription,
        event: PlatformEvent,
    ) -> None:
        try:
            result = subscription.handler(event)
            if inspect.iscoroutine(result):
                asyncio.run(result)
            with self._lock:
                self._delivered_count += 1
        except Exception:
            logger.exception(
                "Event subscriber failed: %s",
                subscription.name or subscription.handler,
            )
