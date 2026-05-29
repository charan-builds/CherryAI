"""Companion interaction schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from database.models import utc_now


@dataclass(frozen=True)
class CompanionMessage:
    """One companion feed message."""

    interaction_type: str
    title: str
    message: str
    priority: str = "normal"
    cooldown_key: str = ""
    context: dict[str, object] = field(default_factory=dict)
    id: str = ""
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class CompanionDecision:
    """Decision for whether to emit a companion message."""

    should_emit: bool
    reason: str
    message: CompanionMessage | None = None
