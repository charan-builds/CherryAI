"""Thread-safe application state store."""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field

from backend.application_state_manager.schemas import (
    STATE_DOMAIN_AI,
    STATE_DOMAIN_AUTOMATION,
    STATE_DOMAIN_EVENTS,
    STATE_DOMAIN_FOCUS,
    STATE_DOMAIN_HEALTH,
    STATE_DOMAIN_NOTIFICATIONS,
    STATE_DOMAIN_STUDY,
    STATE_DOMAIN_WORKFLOWS,
    ApplicationStateSnapshot,
)
from backend.centralized_event_bus.schemas import PlatformEvent
from database.models import utc_now

StateSubscriber = Callable[[ApplicationStateSnapshot], None]


@dataclass
class ApplicationStateManager:
    """Centralized app-wide state with subscriptions and snapshots."""

    subscribers: dict[str, list[StateSubscriber]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self._domains: dict[str, dict[str, object]] = {
            STATE_DOMAIN_WORKFLOWS: {},
            STATE_DOMAIN_STUDY: {},
            STATE_DOMAIN_FOCUS: {},
            STATE_DOMAIN_NOTIFICATIONS: {},
            STATE_DOMAIN_AI: {},
            STATE_DOMAIN_AUTOMATION: {},
            STATE_DOMAIN_HEALTH: {"status": "starting", "degraded": False},
            STATE_DOMAIN_EVENTS: {},
        }
        self._updated_at = utc_now()

    def subscribe(self, domain: str, subscriber: StateSubscriber) -> None:
        """Subscribe to state updates for one domain or '*'."""
        with self._lock:
            self.subscribers[domain].append(subscriber)

    def update_domain(self, domain: str, updates: dict[str, object]) -> None:
        """Merge updates into one state domain."""
        with self._lock:
            current = dict(self._domains.get(domain, {}))
            current.update(deepcopy(updates))
            self._domains[domain] = current
            self._updated_at = utc_now()
            snapshot = self.snapshot()
            subscribers = self._subscribers_for(domain)
        self._notify(subscribers, snapshot)

    def set_item(self, domain: str, key: str, value: object) -> None:
        """Set one value in a state domain."""
        self.update_domain(domain, {key: value})

    def remove_item(self, domain: str, key: str) -> None:
        """Remove one value from a state domain."""
        with self._lock:
            current = dict(self._domains.get(domain, {}))
            current.pop(key, None)
            self._domains[domain] = current
            self._updated_at = utc_now()
            snapshot = self.snapshot()
            subscribers = self._subscribers_for(domain)
        self._notify(subscribers, snapshot)

    def snapshot(self) -> ApplicationStateSnapshot:
        """Return a consistent immutable state snapshot."""
        with self._lock:
            domains = deepcopy(self._domains)
            return ApplicationStateSnapshot(
                active_workflows=domains[STATE_DOMAIN_WORKFLOWS],
                active_study_sessions=domains[STATE_DOMAIN_STUDY],
                focus_state=domains[STATE_DOMAIN_FOCUS],
                active_notifications=domains[STATE_DOMAIN_NOTIFICATIONS],
                ai_context=domains[STATE_DOMAIN_AI],
                automation_state=domains[STATE_DOMAIN_AUTOMATION],
                runtime_health=domains[STATE_DOMAIN_HEALTH],
                event_counters=domains[STATE_DOMAIN_EVENTS],
                updated_at=self._updated_at,
            )

    def handle_event(self, event: PlatformEvent) -> None:
        """Update coarse runtime state from platform events."""
        self._increment_event_counter(event.category)
        if event.category == "workflow":
            self._handle_workflow_event(event)
        elif event.category == "observer":
            self.update_domain(STATE_DOMAIN_FOCUS, event.payload)
        elif event.category == "automation":
            self.update_domain(
                STATE_DOMAIN_AUTOMATION,
                {
                    "last_event": event.event_type,
                    "last_tool": event.payload.get("tool_name", ""),
                    "last_success": event.payload.get("success", None),
                },
            )
        elif event.category == "ai":
            self.update_domain(STATE_DOMAIN_AI, event.payload)
        elif event.category == "notification":
            self.set_item(
                STATE_DOMAIN_NOTIFICATIONS,
                event.id,
                {"message": event.payload.get("message", ""), "level": event.event_type},
            )
        elif event.category in {"lifecycle", "system"}:
            self.update_domain(STATE_DOMAIN_HEALTH, event.payload)

    def _handle_workflow_event(self, event: PlatformEvent) -> None:
        workflow_id = str(event.payload.get("workflow_id", event.correlation_id))
        if not workflow_id:
            return
        if event.event_type in {"workflow_completed", "workflow_failed", "workflow_cancelled"}:
            self.remove_item(STATE_DOMAIN_WORKFLOWS, workflow_id)
            return
        self.set_item(
            STATE_DOMAIN_WORKFLOWS,
            workflow_id,
            {
                "workflow_id": workflow_id,
                "event_type": event.event_type,
                "step_key": event.payload.get("step_key", ""),
                "message": event.payload.get("message", ""),
                "updated_at": event.created_at.isoformat(),
            },
        )

    def _increment_event_counter(self, category: str) -> None:
        with self._lock:
            counters = dict(self._domains[STATE_DOMAIN_EVENTS])
            counters[category] = int(counters.get(category, 0)) + 1
            self._domains[STATE_DOMAIN_EVENTS] = counters
            self._updated_at = utc_now()

    def _subscribers_for(self, domain: str) -> list[StateSubscriber]:
        subscribers = list(self.subscribers.get(domain, []))
        subscribers.extend(self.subscribers.get("*", []))
        return subscribers

    def _notify(
        self,
        subscribers: list[StateSubscriber],
        snapshot: ApplicationStateSnapshot,
    ) -> None:
        for subscriber in subscribers:
            subscriber(snapshot)
