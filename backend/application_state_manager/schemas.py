"""Application-wide state models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from database.models import utc_now

STATE_DOMAIN_WORKFLOWS = "workflows"
STATE_DOMAIN_STUDY = "study"
STATE_DOMAIN_FOCUS = "focus"
STATE_DOMAIN_NOTIFICATIONS = "notifications"
STATE_DOMAIN_AI = "ai"
STATE_DOMAIN_AUTOMATION = "automation"
STATE_DOMAIN_HEALTH = "health"
STATE_DOMAIN_EVENTS = "events"


@dataclass(frozen=True)
class ApplicationStateSnapshot:
    """Immutable snapshot of runtime state for services and UI."""

    active_workflows: dict[str, dict[str, object]] = field(default_factory=dict)
    active_study_sessions: dict[str, dict[str, object]] = field(default_factory=dict)
    focus_state: dict[str, object] = field(default_factory=dict)
    active_notifications: dict[str, dict[str, object]] = field(default_factory=dict)
    ai_context: dict[str, object] = field(default_factory=dict)
    automation_state: dict[str, object] = field(default_factory=dict)
    runtime_health: dict[str, object] = field(default_factory=dict)
    event_counters: dict[str, int] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=utc_now)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly dictionary."""
        return {
            "active_workflows": self.active_workflows,
            "active_study_sessions": self.active_study_sessions,
            "focus_state": self.focus_state,
            "active_notifications": self.active_notifications,
            "ai_context": self.ai_context,
            "automation_state": self.automation_state,
            "runtime_health": self.runtime_health,
            "event_counters": self.event_counters,
            "updated_at": self.updated_at.isoformat(),
        }
