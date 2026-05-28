"""Daily summary DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class DailyProductivitySummary:
    """Daily productivity, focus, task, and study report."""

    summary_date: date
    productivity_score: float
    consistency_score: float
    focus_score: float
    completed_tasks: int
    open_tasks: int
    study_duration_seconds: float
    focus_duration_seconds: float
    distraction_count: int
    interruption_count: int
    summary_text: str
    focus_report: str
    task_report: str
    study_statistics: dict[str, object] = field(default_factory=dict)
    ai_insight: str = ""
