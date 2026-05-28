"""Study session lifecycle management."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from database.models import utc_now
from backend.observer_engine.observer_event_bus.events import (
    STUDY_COMPLETED,
    STUDY_STARTED,
    ObserverEvent,
)
from backend.observer_engine.observer_event_bus.service import ObserverEventBus
from backend.observer_engine.observer_state_manager.service import ObserverStateManager
from backend.observer_engine.schemas import FocusMetrics, IdleSnapshot, StudySessionRecord

logger = logging.getLogger(__name__)


@dataclass
class StudySessionManager:
    """Starts, stops, and reports study sessions."""

    state_manager: ObserverStateManager
    event_bus: ObserverEventBus
    active_session: StudySessionRecord | None = None
    accumulated_idle_seconds: float = 0.0
    last_idle_observed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.active_session = self.state_manager.get_active_study_session()

    def start_session(
        self,
        topic: str,
        metadata: dict[str, object] | None = None,
    ) -> StudySessionRecord:
        """Start a study session."""
        cleaned_topic = topic.strip() or "Untitled study session"
        self.active_session = self.state_manager.create_study_session(
            topic=cleaned_topic,
            metadata=metadata or {},
            started_at=utc_now(),
        )
        self.accumulated_idle_seconds = 0.0
        self.last_idle_observed_at = None
        event = ObserverEvent(
            event_type=STUDY_STARTED,
            payload={"session_id": self.active_session.id, "topic": cleaned_topic},
        )
        self.state_manager.record_event(event)
        self.event_bus.publish(event)
        logger.info("Study session started: %s", self.active_session.id)
        return self.active_session

    def stop_session(self, focus_metrics: FocusMetrics) -> StudySessionRecord | None:
        """Stop the active study session."""
        if self.active_session is None:
            return None

        completed = self.state_manager.complete_study_session(
            session_id=self.active_session.id,
            ended_at=utc_now(),
            focus_seconds=focus_metrics.focus_seconds,
            idle_seconds=self.accumulated_idle_seconds,
            interruption_count=focus_metrics.interruption_count,
        )
        if completed is None:
            return None

        event = ObserverEvent(
            event_type=STUDY_COMPLETED,
            payload={
                "session_id": completed.id,
                "topic": completed.topic,
                "duration_seconds": completed.duration_seconds,
                "focus_seconds": completed.focus_seconds,
                "interruption_count": completed.interruption_count,
            },
        )
        self.state_manager.record_event(event)
        self.event_bus.publish(event)
        self.active_session = None
        logger.info("Study session completed: %s", completed.id)
        return completed

    def update_idle(self, idle_snapshot: IdleSnapshot) -> None:
        """Accumulate idle time during active study."""
        if self.active_session is None:
            self.last_idle_observed_at = idle_snapshot.observed_at
            return

        if self.last_idle_observed_at is not None and idle_snapshot.is_idle:
            elapsed = max(
                (idle_snapshot.observed_at - self.last_idle_observed_at).total_seconds(),
                0.0,
            )
            self.accumulated_idle_seconds += elapsed

        self.last_idle_observed_at = idle_snapshot.observed_at

    def is_active(self) -> bool:
        """Return whether a study session is currently active."""
        return self.active_session is not None
