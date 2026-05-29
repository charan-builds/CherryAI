"""Typed platform event models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from database.models import utc_now

EVENT_CATEGORY_WORKFLOW = "workflow"
EVENT_CATEGORY_OBSERVER = "observer"
EVENT_CATEGORY_AUTOMATION = "automation"
EVENT_CATEGORY_AI = "ai"
EVENT_CATEGORY_MEMORY = "memory"
EVENT_CATEGORY_KNOWLEDGE = "knowledge"
EVENT_CATEGORY_NOTIFICATION = "notification"
EVENT_CATEGORY_LIFECYCLE = "lifecycle"
EVENT_CATEGORY_SYSTEM = "system"

PRIORITY_LOW = 10
PRIORITY_NORMAL = 50
PRIORITY_HIGH = 80
PRIORITY_CRITICAL = 100


@dataclass(frozen=True)
class PlatformEvent:
    """Unified event envelope used by Cherry AI platform services."""

    event_type: str
    source: str
    category: str
    payload: dict[str, object] = field(default_factory=dict)
    priority: int = PRIORITY_NORMAL
    id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = ""
    parent_event_id: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def with_payload(self, **updates: object) -> "PlatformEvent":
        """Return a copy with additional payload fields."""
        payload = dict(self.payload)
        payload.update(updates)
        return PlatformEvent(
            id=self.id,
            trace_id=self.trace_id,
            correlation_id=self.correlation_id,
            parent_event_id=self.parent_event_id,
            event_type=self.event_type,
            source=self.source,
            category=self.category,
            payload=payload,
            priority=self.priority,
            created_at=self.created_at,
        )


@dataclass(frozen=True)
class EventFilter:
    """Subscription filter for event consumers."""

    categories: tuple[str, ...] = ()
    event_types: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    min_priority: int = PRIORITY_LOW

    def matches(self, event: PlatformEvent) -> bool:
        """Return whether an event should be delivered."""
        if event.priority < self.min_priority:
            return False
        if self.categories and event.category not in self.categories:
            return False
        if self.event_types and event.event_type not in self.event_types:
            return False
        if self.sources and event.source not in self.sources:
            return False
        return True


@dataclass(frozen=True)
class EventBusMetrics:
    """Lightweight event bus counters."""

    published_count: int
    delivered_count: int
    dropped_count: int
    subscriber_count: int
    history_size: int
