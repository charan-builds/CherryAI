"""Context retrieval DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ContextItem:
    """One retrievable context item with source metadata."""

    source: str
    title: str
    content: str
    category: str
    created_at: datetime
    updated_at: datetime | None = None
    importance: float = 0.5
    repetition_count: int = 1
    behavioral_significance: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoredContextItem:
    """Context item plus deterministic relevance score."""

    item: ContextItem
    score: float


@dataclass(frozen=True)
class RetrievedContext:
    """Ranked retrieved context for a user request."""

    query: str
    items: list[ScoredContextItem] = field(default_factory=list)
