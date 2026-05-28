"""Memory classification DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field


MEMORY_EPISODIC = "episodic"
MEMORY_BEHAVIORAL = "behavioral"
MEMORY_SEMANTIC = "semantic"
MEMORY_WORKING = "working"

SUPPORTED_MEMORY_CATEGORIES = {
    MEMORY_EPISODIC,
    MEMORY_BEHAVIORAL,
    MEMORY_SEMANTIC,
    MEMORY_WORKING,
}


@dataclass(frozen=True)
class MemoryClassificationInput:
    """Raw memory signal to classify."""

    text: str
    source_type: str = "manual"
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryClassificationResult:
    """Deterministic memory category and explanation."""

    category: str
    confidence: float
    reason: str
    importance_hint: float
