"""Focus and distraction tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from backend.observer_engine.observer_event_bus.events import (
    DISTRACTION_DETECTED,
    FOCUS_LOST,
    ObserverEvent,
)
from backend.observer_engine.schemas import FocusMetrics, IdleSnapshot, WindowSnapshot


@dataclass
class FocusTracker:
    """Tracks app switching, focus time, and distractions."""

    distraction_keywords: tuple[str, ...]
    app_switch_count: int = 0
    distraction_count: int = 0
    focus_seconds: float = 0.0
    interruption_count: int = 0
    last_window: WindowSnapshot | None = None
    last_observed_at: datetime | None = None
    active_distractions: set[str] = field(default_factory=set)

    def sample(
        self,
        window: WindowSnapshot,
        idle: IdleSnapshot,
        study_active: bool,
    ) -> tuple[FocusMetrics, list[ObserverEvent]]:
        """Update focus metrics from the latest observer snapshots."""
        events: list[ObserverEvent] = []
        elapsed = self._elapsed_since_last(window)
        app_changed = self._app_changed(window)

        if elapsed > 0 and not idle.is_idle and not self._is_distraction(window):
            self.focus_seconds += elapsed

        if app_changed and self.last_window is not None:
            self.app_switch_count += 1
            if study_active:
                self.interruption_count += 1
                events.append(
                    ObserverEvent(
                        event_type=FOCUS_LOST,
                        payload={
                            "application_name": window.application_name,
                            "window_title": window.window_title,
                            "app_switch_count": self.app_switch_count,
                        },
                        created_at=window.observed_at,
                    )
                )

        distraction_key = self._distraction_key(window)
        if study_active and distraction_key and distraction_key not in self.active_distractions:
            self.active_distractions.add(distraction_key)
            self.distraction_count += 1
            self.interruption_count += 1
            events.append(
                ObserverEvent(
                    event_type=DISTRACTION_DETECTED,
                    payload={
                        "application_name": window.application_name,
                        "window_title": window.window_title,
                        "keyword": distraction_key,
                    },
                    created_at=window.observed_at,
                )
            )

        self.last_window = window
        self.last_observed_at = window.observed_at
        return self.metrics(current_focus_seconds=elapsed if not idle.is_idle else 0.0), events

    def reset_session_metrics(self) -> None:
        """Reset focus metrics for a new study session."""
        self.app_switch_count = 0
        self.distraction_count = 0
        self.focus_seconds = 0.0
        self.interruption_count = 0
        self.active_distractions.clear()

    def metrics(self, current_focus_seconds: float = 0.0) -> FocusMetrics:
        """Return current metrics."""
        return FocusMetrics(
            app_switch_count=self.app_switch_count,
            distraction_count=self.distraction_count,
            focus_seconds=self.focus_seconds,
            interruption_count=self.interruption_count,
            current_focus_seconds=current_focus_seconds,
        )

    def _elapsed_since_last(self, window: WindowSnapshot) -> float:
        if self.last_observed_at is None:
            return 0.0
        return max((window.observed_at - self.last_observed_at).total_seconds(), 0.0)

    def _app_changed(self, window: WindowSnapshot) -> bool:
        if self.last_window is None:
            return False
        return (
            self.last_window.application_name != window.application_name
            or self.last_window.window_title != window.window_title
        )

    def _is_distraction(self, window: WindowSnapshot) -> bool:
        return bool(self._distraction_key(window))

    def _distraction_key(self, window: WindowSnapshot) -> str:
        haystack = f"{window.application_name} {window.window_title}".lower()
        for keyword in self.distraction_keywords:
            normalized = keyword.strip().lower()
            if normalized and normalized in haystack:
                return normalized
        return ""
