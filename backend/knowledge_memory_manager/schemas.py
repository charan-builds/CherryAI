"""Schemas for knowledge memories."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class KnowledgeMemoryCreate:
    """Input for storing a knowledge memory."""

    source_type: str
    source_name: str
    title: str
    summary: str
    notes: tuple[str, ...] = ()
    concepts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeMemoryRecord:
    """Persisted knowledge memory record."""

    id: str
    source_type: str
    source_name: str
    title: str
    summary: str
    notes: tuple[str, ...]
    concepts: tuple[str, ...]
    tags: tuple[str, ...]
    content_hash: str
    semantic_memory_id: str
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime
