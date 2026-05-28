"""Observer engine data transfer objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WindowSnapshot:
    """Current active window state."""

    application_name: str
    window_title: str
    observed_at: datetime


@dataclass(frozen=True)
class IdleSnapshot:
    """Current keyboard/mouse idle state."""

    idle_seconds: float
    is_idle: bool
    observed_at: datetime


@dataclass(frozen=True)
class FocusMetrics:
    """Focus tracker metrics for the current process lifetime."""

    app_switch_count: int
    distraction_count: int
    focus_seconds: float
    interruption_count: int
    current_focus_seconds: float


@dataclass(frozen=True)
class StudySessionRecord:
    """Persisted study session DTO."""

    id: str
    topic: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: float
    focus_seconds: float
    idle_seconds: float
    interruption_count: int


@dataclass(frozen=True)
class ObserverStatus:
    """Current observer state summary for UI rendering."""

    active_app: str
    window_title: str
    idle_seconds: float
    is_idle: bool
    app_switch_count: int
    distraction_count: int
    focus_seconds: float
    current_focus_seconds: float
    active_study_session: StudySessionRecord | None
