"""Productivity analyzer data transfer objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from backend.focus_scoring_engine.schemas import FocusScoreResult


@dataclass(frozen=True)
class ProductivityAnalysis:
    """Daily deterministic productivity metrics."""

    analysis_date: date
    created_tasks: int
    completed_tasks: int
    open_tasks: int
    study_duration_seconds: float
    focus_duration_seconds: float
    idle_seconds: float
    app_usage_seconds: dict[str, float] = field(default_factory=dict)
    distraction_count: int = 0
    interruption_count: int = 0
    productivity_score: float = 0.0
    consistency_score: float = 0.0
    focus_score: float = 0.0
    focus_metrics: FocusScoreResult | None = None
