"""Focus scoring data transfer objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FocusScoreInput:
    """Raw deterministic inputs used to score a focus session."""

    session_duration_seconds: float
    focus_duration_seconds: float
    interruption_count: int
    distraction_count: int
    idle_seconds: float = 0.0


@dataclass(frozen=True)
class FocusScoreResult:
    """Calculated focus metrics and the final 0-100 score."""

    focus_duration_seconds: float
    focus_ratio: float
    interruption_rate: float
    distraction_severity: float
    session_quality: float
    focus_score: float
