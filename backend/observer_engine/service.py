"""Observer engine composition service."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.observer_engine.active_window_tracker.service import (
    ActiveWindowProvider,
    ActiveWindowTracker,
    WindowsActiveWindowProvider,
)
from backend.observer_engine.focus_tracker.service import FocusTracker
from backend.observer_engine.idle_detector.service import (
    IdleDetector,
    IdleProvider,
    WindowsIdleProvider,
)
from backend.observer_engine.observer_event_bus.events import APP_CHANGED, ObserverEvent
from backend.observer_engine.observer_event_bus.service import ObserverEventBus
from backend.observer_engine.observer_state_manager.service import ObserverStateManager
from backend.observer_engine.schemas import (
    FocusMetrics,
    IdleSnapshot,
    ObserverStatus,
    StudySessionRecord,
    WindowSnapshot,
)
from backend.observer_engine.study_session_manager.service import StudySessionManager

logger = logging.getLogger(__name__)


@dataclass
class ObserverEngine:
    """Coordinates local activity, focus, idle, and study tracking."""

    settings: AppSettings
    active_window_provider: ActiveWindowProvider | None = None
    idle_provider: IdleProvider | None = None
    event_bus: ObserverEventBus | None = None
    state_manager: ObserverStateManager | None = None

    def __post_init__(self) -> None:
        self.event_bus = self.event_bus or ObserverEventBus()
        self.state_manager = self.state_manager or ObserverStateManager(self.settings)
        self.active_window_tracker = ActiveWindowTracker(
            provider=self.active_window_provider or WindowsActiveWindowProvider()
        )
        self.idle_detector = IdleDetector(
            provider=self.idle_provider or WindowsIdleProvider(),
            idle_threshold_seconds=self.settings.idle_threshold_seconds,
        )
        self.focus_tracker = FocusTracker(
            distraction_keywords=self.settings.distraction_keywords,
        )
        self.study_sessions = StudySessionManager(
            state_manager=self.state_manager,
            event_bus=self.event_bus,
        )
        self.last_window = WindowSnapshot("Unknown", "", self._now())
        self.last_idle = IdleSnapshot(0.0, False, self._now())
        self.last_focus_metrics = FocusMetrics(0, 0, 0.0, 0, 0.0)

    def sample_once(self) -> ObserverStatus:
        """Poll observer providers once and persist resulting state."""
        if not self.settings.observer_enabled:
            return self.get_status()

        try:
            window, app_event = self.active_window_tracker.sample()
            idle, idle_event = self.idle_detector.sample()
            self.study_sessions.update_idle(idle)
            focus_metrics, focus_events = self.focus_tracker.sample(
                window=window,
                idle=idle,
                study_active=self.study_sessions.is_active(),
            )

            app_changed = self.state_manager.record_window_snapshot(window)
            events = list(focus_events)
            if app_event is not None and app_changed:
                events.append(app_event)
            if idle_event is not None:
                events.append(idle_event)

            for event in events:
                self._record_and_publish(event)

            self.last_window = window
            self.last_idle = idle
            self.last_focus_metrics = focus_metrics
            return self.get_status()
        except Exception:
            logger.exception("Observer sample failed")
            return self.get_status()

    def start_study_session(
        self,
        topic: str,
        metadata: dict[str, object] | None = None,
    ) -> StudySessionRecord:
        """Start a study session and reset focus metrics."""
        self.focus_tracker.reset_session_metrics()
        session = self.study_sessions.start_session(topic, metadata)
        self.last_focus_metrics = self.focus_tracker.metrics()
        return session

    def stop_study_session(self) -> StudySessionRecord | None:
        """Stop the active study session."""
        completed = self.study_sessions.stop_session(self.last_focus_metrics)
        self.last_focus_metrics = self.focus_tracker.metrics()
        return completed

    def get_status(self) -> ObserverStatus:
        """Return the latest observer status for UI rendering."""
        return ObserverStatus(
            active_app=self.last_window.application_name,
            window_title=self.last_window.window_title,
            idle_seconds=self.last_idle.idle_seconds,
            is_idle=self.last_idle.is_idle,
            app_switch_count=self.last_focus_metrics.app_switch_count,
            distraction_count=self.last_focus_metrics.distraction_count,
            focus_seconds=self.last_focus_metrics.focus_seconds,
            current_focus_seconds=self.last_focus_metrics.current_focus_seconds,
            active_study_session=self.study_sessions.active_session,
        )

    def snapshot(self) -> dict[str, str]:
        """Return a minimal agent-friendly observer snapshot."""
        status = self.get_status()
        return {
            "environment": self.settings.app_env,
            "active_app": status.active_app,
            "window_title": status.window_title,
            "is_idle": str(status.is_idle),
        }

    def subscribe(self, event_type: str, handler) -> None:
        """Subscribe to observer events."""
        self.event_bus.subscribe(event_type, handler)

    def _record_and_publish(self, event: ObserverEvent) -> None:
        self.state_manager.record_event(event)
        self.event_bus.publish(event)

    def _now(self):
        from database.models import utc_now

        return utc_now()
