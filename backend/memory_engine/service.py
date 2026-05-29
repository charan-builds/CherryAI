"""Advanced memory and context engine facade."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_MEMORY,
    PRIORITY_LOW,
    PlatformEvent,
)
from backend.centralized_event_bus.service import CentralizedEventBus
from backend.context_injection_engine.service import ContextInjectionEngine
from backend.context_retriever.service import ContextRetriever
from backend.memory_classifier.service import MemoryClassifier
from backend.memory_consolidation_engine.service import MemoryConsolidationEngine
from backend.memory_scoring_engine.service import MemoryScoringEngine
from backend.observer_engine.schemas import ObserverStatus
from backend.semantic_memory_manager.service import SemanticMemoryManager
from backend.working_memory_manager.service import WorkingMemoryManager

logger = logging.getLogger(__name__)


@dataclass
class MemoryEngine:
    """Facade over Cherry's advanced memory and context subsystems."""

    settings: AppSettings
    classifier: MemoryClassifier | None = None
    scoring_engine: MemoryScoringEngine | None = None
    semantic_memory: SemanticMemoryManager | None = None
    working_memory: WorkingMemoryManager | None = None
    context_retriever: ContextRetriever | None = None
    context_injection: ContextInjectionEngine | None = None
    consolidation_engine: MemoryConsolidationEngine | None = None
    event_bus: CentralizedEventBus | None = None

    def __post_init__(self) -> None:
        self.classifier = self.classifier or MemoryClassifier()
        self.scoring_engine = self.scoring_engine or MemoryScoringEngine()
        self.semantic_memory = self.semantic_memory or SemanticMemoryManager(
            settings=self.settings,
            classifier=self.classifier,
        )
        self.working_memory = self.working_memory or WorkingMemoryManager(
            settings=self.settings,
        )
        self.context_retriever = self.context_retriever or ContextRetriever(
            settings=self.settings,
            scoring_engine=self.scoring_engine,
        )
        self.context_injection = self.context_injection or ContextInjectionEngine(
            settings=self.settings,
            context_retriever=self.context_retriever,
        )
        self.consolidation_engine = self.consolidation_engine or MemoryConsolidationEngine(
            settings=self.settings,
            semantic_memory_manager=self.semantic_memory,
        )

    def remember(self, item: str) -> None:
        """Store a user-provided memory item."""
        self.semantic_memory.remember(item)
        self._publish_event("memory_stored", {"content_length": len(item)})

    def recent(self, limit: int = 10) -> list[str]:
        """Return recent durable memory text for compatibility callers."""
        return [
            memory.content
            for memory in self.semantic_memory.list_memories(limit=limit)
        ]

    def build_prompt_context(
        self,
        user_message: str,
        session_id: str | None = None,
    ) -> str:
        """Return token-safe memory context for prompt injection."""
        if not self.settings.memory_enabled:
            return "No relevant memory context."
        return self.context_injection.build_prompt_context(
            user_message=user_message,
            session_id=session_id,
        ).text

    def update_conversation(self, session_id: str, user_message: str) -> None:
        """Track active conversation context."""
        if self.settings.memory_enabled:
            self.working_memory.update_conversation(session_id, user_message)
            self._publish_event(
                "working_memory_updated",
                {"session_id": session_id, "content_length": len(user_message)},
            )

    def update_observer_status(self, status: ObserverStatus) -> None:
        """Track active study and focus context."""
        if self.settings.memory_enabled:
            self.working_memory.update_observer_status(status)

    def consolidate(self) -> None:
        """Run a safe consolidation pass and prune stale low-value memories."""
        if not self.settings.memory_enabled:
            return
        self.consolidation_engine.consolidate()
        pruned = self.semantic_memory.prune()
        if pruned:
            logger.info("Pruned %s stale memory item(s)", pruned)
        self._publish_event("memory_consolidated", {"pruned": pruned})

    def _publish_event(self, event_type: str, payload: dict[str, object]) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            PlatformEvent(
                event_type=event_type,
                source="memory_engine",
                category=EVENT_CATEGORY_MEMORY,
                priority=PRIORITY_LOW,
                payload=payload,
            )
        )
