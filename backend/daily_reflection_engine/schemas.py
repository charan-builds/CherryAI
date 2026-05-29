"""Daily reflection schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class DailyReflection:
    """End-of-day companion reflection."""

    reflection_date: date
    study_duration_minutes: int
    focus_score: float
    distractions: int
    completed_tasks: int
    recommendation_effectiveness: float
    summary_text: str
    card_items: tuple[str, ...] = field(default_factory=tuple)
