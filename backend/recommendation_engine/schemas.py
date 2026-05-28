"""Recommendation DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


RECOMMENDATION_START_STUDY = "start_study_session"
RECOMMENDATION_TAKE_BREAK = "take_break"
RECOMMENDATION_CONTINUE_TASK = "continue_task"
RECOMMENDATION_REDUCE_DISTRACTIONS = "reduce_distractions"
RECOMMENDATION_RESUME_FOCUS = "resume_focus"


@dataclass(frozen=True)
class Recommendation:
    """A gentle proactive coaching suggestion."""

    recommendation_type: str
    title: str
    message: str
    priority: str
    cooldown_key: str
    context: dict[str, object] = field(default_factory=dict)
    id: str | None = None
    created_at: datetime | None = None
