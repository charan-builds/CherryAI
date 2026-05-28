"""Memory scoring DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MemoryScoreInput:
    """Raw inputs used to score a memory candidate."""

    content: str
    query: str
    created_at: datetime
    updated_at: datetime | None = None
    importance: float = 0.5
    repetition_count: int = 1
    behavioral_significance: float = 0.0
    interaction_relevance: float = 0.0


@dataclass(frozen=True)
class MemoryScoreResult:
    """Score components and final 0-100 ranking score."""

    score: float
    relevance_score: float
    recency_score: float
    importance_score: float
    repetition_score: float
    behavioral_score: float
    interaction_score: float
