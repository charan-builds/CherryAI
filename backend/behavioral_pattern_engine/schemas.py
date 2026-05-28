"""Behavioral pattern DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class BehavioralPatternRecord:
    """Persisted learned behavior pattern."""

    id: str
    pattern_type: str
    pattern_key: str
    description: str
    confidence: float
    sample_size: int
    metadata: dict[str, object] = field(default_factory=dict)
    last_seen_at: datetime | None = None


@dataclass(frozen=True)
class BehavioralInsights:
    """Grouped patterns for recommendation and summary generation."""

    preferred_study_times: list[BehavioralPatternRecord] = field(default_factory=list)
    distraction_windows: list[BehavioralPatternRecord] = field(default_factory=list)
    productive_periods: list[BehavioralPatternRecord] = field(default_factory=list)
    common_interruptions: list[BehavioralPatternRecord] = field(default_factory=list)
