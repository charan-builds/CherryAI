"""Memory consolidation DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConsolidatedPatternRecord:
    """Learned pattern produced by consolidation."""

    id: str
    pattern_type: str
    pattern_key: str
    title: str
    insight: str
    confidence: float
    evidence_count: int
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryConsolidationResult:
    """Result of one consolidation pass."""

    patterns: list[ConsolidatedPatternRecord] = field(default_factory=list)
    semantic_memories_created: int = 0
