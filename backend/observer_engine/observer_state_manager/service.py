"""Observer state management."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.observer_engine.observer_event_bus.events import ObserverEvent
from backend.observer_engine.observer_state_manager.repository import (
    ObserverStateRepository,
)
from backend.observer_engine.schemas import StudySessionRecord, WindowSnapshot

logger = logging.getLogger(__name__)


@dataclass
class ObserverStateManager:
    """Keeps current observer state and persists durable records."""

    settings: AppSettings
    repository: ObserverStateRepository | None = None
    current_activity_id: str | None = None
    current_window: WindowSnapshot | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = ObserverStateRepository.from_settings(self.settings)

    def record_window_snapshot(self, snapshot: WindowSnapshot) -> bool:
        """Persist app changes as activity intervals.

        Returns True when the active app/window changed.
        """
        if self.current_window is None:
            self.current_activity_id = self.repository.start_activity(
                snapshot.application_name,
                snapshot.window_title,
                snapshot.observed_at,
            )
            self.current_window = snapshot
            return True

        if (
            self.current_window.application_name == snapshot.application_name
            and self.current_window.window_title == snapshot.window_title
        ):
            return False

        if self.current_activity_id is not None:
            self.repository.end_activity(self.current_activity_id, snapshot.observed_at)

        self.current_activity_id = self.repository.start_activity(
            snapshot.application_name,
            snapshot.window_title,
            snapshot.observed_at,
        )
        self.current_window = snapshot
        return True

    def record_event(self, event: ObserverEvent) -> None:
        """Persist an observer event."""
        self.repository.record_event(
            event.event_type,
            event.payload,
            event.created_at,
        )

    def create_study_session(
        self,
        topic: str,
        metadata: dict[str, object],
        started_at,
    ) -> StudySessionRecord:
        """Create a study session."""
        return self.repository.create_study_session(topic, metadata, started_at)

    def complete_study_session(
        self,
        session_id: str,
        ended_at,
        focus_seconds: float,
        idle_seconds: float,
        interruption_count: int,
    ) -> StudySessionRecord | None:
        """Complete a study session."""
        return self.repository.complete_study_session(
            session_id=session_id,
            ended_at=ended_at,
            focus_seconds=focus_seconds,
            idle_seconds=idle_seconds,
            interruption_count=interruption_count,
        )

    def get_active_study_session(self) -> StudySessionRecord | None:
        """Return active study session, if one exists."""
        return self.repository.get_active_study_session()
