"""Semantic memory DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SemanticMemoryRecord:
    """Durable memory record returned by the semantic manager."""

    id: str
    category: str
    title: str
    content: str
    source_type: str
    source_id: str
    importance: float
    confidence: float
    repetition_count: int
    behavioral_significance: float
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class SemanticMemoryCreate:
    """Data needed to create or reinforce a semantic memory."""

    category: str
    title: str
    content: str
    source_type: str = "manual"
    source_id: str = ""
    importance: float = 0.5
    confidence: float = 0.5
    behavioral_significance: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)
