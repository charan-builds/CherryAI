"""Semantic memory manager."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.memory_classifier.schemas import MemoryClassificationInput
from backend.memory_classifier.service import MemoryClassifier
from backend.semantic_memory_manager.repository import SemanticMemoryRepository
from backend.semantic_memory_manager.schemas import (
    SemanticMemoryCreate,
    SemanticMemoryRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class SemanticMemoryManager:
    """Stores learned preferences, habits, productivity traits, and patterns."""

    settings: AppSettings
    classifier: MemoryClassifier
    repository: SemanticMemoryRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = SemanticMemoryRepository.from_settings(self.settings)

    def remember(
        self,
        text: str,
        title: str = "",
        source_type: str = "manual",
        source_id: str = "",
        importance: float | None = None,
        confidence: float | None = None,
        behavioral_significance: float = 0.0,
        metadata: dict[str, object] | None = None,
    ) -> SemanticMemoryRecord:
        """Classify and persist a durable memory."""
        classification = self.classifier.classify(
            MemoryClassificationInput(
                text=text,
                source_type=source_type,
                metadata=metadata or {},
            )
        )
        record = self.repository.remember(
            SemanticMemoryCreate(
                category=classification.category,
                title=title.strip() or self._title_from_text(text),
                content=text.strip(),
                source_type=source_type,
                source_id=source_id,
                importance=importance if importance is not None else classification.importance_hint,
                confidence=confidence if confidence is not None else classification.confidence,
                behavioral_significance=behavioral_significance,
                metadata={
                    "classification_reason": classification.reason,
                    **(metadata or {}),
                },
            )
        )
        logger.info("Stored semantic memory: %s", record.id)
        return record

    def list_memories(
        self,
        categories: tuple[str, ...] | None = None,
        limit: int = 50,
    ) -> list[SemanticMemoryRecord]:
        """List learned memories."""
        return self.repository.list_memories(categories=categories, limit=limit)

    def prune(self) -> int:
        """Safely prune stale low-confidence memories."""
        return self.repository.prune_older_than(
            retention_days=self.settings.memory_retention_days,
            limit=self.settings.memory_prune_batch_size,
        )

    def _title_from_text(self, text: str) -> str:
        cleaned = " ".join(text.strip().split())
        if len(cleaned) <= 80:
            return cleaned or "Memory"
        return f"{cleaned[:77]}..."
