"""Contextual companion recommendation schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from database.models import utc_now


@dataclass(frozen=True)
class ContextualRecommendation:
    """Personalized recommendation shown in companion feed."""

    title: str
    message: str
    reason: str
    priority: str = "normal"
    cooldown_key: str = ""
    context: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
