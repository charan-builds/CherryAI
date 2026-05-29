"""Startup briefing schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from database.models import utc_now


@dataclass(frozen=True)
class StartupBriefing:
    """Morning/startup briefing shown when Cherry opens."""

    greeting: str
    pending_tasks: tuple[str, ...]
    active_goals: tuple[str, ...]
    focus_score_trend: str
    yesterday_summary: str
    suggested_first_action: str
    generated_at: datetime = field(default_factory=utc_now)
