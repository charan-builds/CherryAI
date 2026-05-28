"""Observer event schemas and constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from database.models import utc_now

APP_CHANGED = "app_changed"
IDLE_DETECTED = "idle_detected"
FOCUS_LOST = "focus_lost"
STUDY_STARTED = "study_started"
STUDY_COMPLETED = "study_completed"
DISTRACTION_DETECTED = "distraction_detected"

SUPPORTED_OBSERVER_EVENTS = {
    APP_CHANGED,
    IDLE_DETECTED,
    FOCUS_LOST,
    STUDY_STARTED,
    STUDY_COMPLETED,
    DISTRACTION_DETECTED,
}


@dataclass(frozen=True)
class ObserverEvent:
    """Event emitted by observer services."""

    event_type: str
    payload: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
