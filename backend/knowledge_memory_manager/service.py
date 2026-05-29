"""Knowledge memory manager that bridges summaries into semantic memory."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_KNOWLEDGE,
    PRIORITY_LOW,
    PlatformEvent,
)
from backend.centralized_event_bus.service import CentralizedEventBus
from backend.knowledge_memory_manager.repository import KnowledgeMemoryRepository
from backend.knowledge_memory_manager.schemas import (
    KnowledgeMemoryCreate,
    KnowledgeMemoryRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeMemoryManager:
    """Stores knowledge artifacts and links them to long-term memory."""

    settings: AppSettings
    repository: KnowledgeMemoryRepository | None = None
    memory_engine: object | None = None
    event_bus: CentralizedEventBus | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or KnowledgeMemoryRepository.from_settings(
            self.settings
        )

    def store_summary(
        self,
        source_type: str,
        source_name: str,
        title: str,
        summary: str,
        notes: tuple[str, ...] = (),
        concepts: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        metadata: dict[str, object] | None = None,
    ) -> KnowledgeMemoryRecord:
        """Persist a summary and mirror it into semantic memory when available."""
        record = self.repository.upsert(
            KnowledgeMemoryCreate(
                source_type=source_type,
                source_name=source_name,
                title=title,
                summary=summary,
                notes=notes,
                concepts=concepts,
                tags=tags,
                metadata=metadata or {},
            )
        )
        linked = self._link_semantic_memory(record)
        self._publish_event(
            "knowledge_memory_stored",
            {
                "record_id": linked.id,
                "source_type": linked.source_type,
                "concept_count": len(linked.concepts),
            },
        )
        return linked

    def store_notes(
        self,
        source_name: str,
        title: str,
        notes: tuple[str, ...],
        concepts: tuple[str, ...] = (),
    ) -> KnowledgeMemoryRecord:
        """Persist user-facing notes as a knowledge memory."""
        summary = " ".join(notes) if notes else title
        return self.store_summary(
            source_type="notes",
            source_name=source_name,
            title=title,
            summary=summary,
            notes=notes,
            concepts=concepts,
            tags=("notes", "knowledge"),
        )

    def list_recent(self, limit: int = 20) -> list[KnowledgeMemoryRecord]:
        """Return recent knowledge memories."""
        return self.repository.list_recent(limit=limit)

    def _link_semantic_memory(
        self,
        record: KnowledgeMemoryRecord,
    ) -> KnowledgeMemoryRecord:
        if not getattr(self.settings, "knowledge_memory_enabled", True):
            return record
        semantic = getattr(self.memory_engine, "semantic_memory", None)
        if semantic is None:
            return record

        memory_text = (
            f"{record.title}: {record.summary} "
            f"Concepts: {', '.join(record.concepts[:8])}"
        ).strip()
        try:
            semantic_record = semantic.remember(
                memory_text,
                title=record.title,
                source_type="knowledge",
                source_id=record.id,
                importance=0.65,
                confidence=0.7,
                metadata={
                    "knowledge_source_type": record.source_type,
                    "knowledge_source_name": record.source_name,
                    "tags": list(record.tags),
                },
            )
        except Exception:
            logger.exception("Failed to link knowledge memory into semantic memory")
            return record

        updated = self.repository.update_semantic_link(record.id, semantic_record.id)
        return updated or record

    def _publish_event(self, event_type: str, payload: dict[str, object]) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            PlatformEvent(
                event_type=event_type,
                source="knowledge_memory_manager",
                category=EVENT_CATEGORY_KNOWLEDGE,
                priority=PRIORITY_LOW,
                payload=payload,
            )
        )
