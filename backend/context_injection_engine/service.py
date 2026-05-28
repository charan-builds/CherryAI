"""Prompt context injection."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.context_injection_engine.schemas import PromptContext
from backend.context_retriever.schemas import RetrievedContext, ScoredContextItem
from backend.context_retriever.service import ContextRetriever

logger = logging.getLogger(__name__)


@dataclass
class ContextInjectionEngine:
    """Builds token-safe prompt context from ranked memory retrieval."""

    settings: AppSettings
    context_retriever: ContextRetriever

    def build_prompt_context(
        self,
        user_message: str,
        session_id: str | None = None,
    ) -> PromptContext:
        """Retrieve and format relevant context for an Ollama prompt."""
        retrieved = self.context_retriever.retrieve(
            query=user_message,
            session_id=session_id,
        )
        return self.from_retrieved_context(retrieved)

    def from_retrieved_context(self, retrieved: RetrievedContext) -> PromptContext:
        """Format an existing retrieval result within the configured budget."""
        max_chars = max(self.settings.memory_context_max_chars, 200)
        if not retrieved.items:
            return PromptContext(text="No relevant memory context.", included_items=[])

        lines = ["Relevant Cherry memory context:"]
        included: list[ScoredContextItem] = []
        trimmed = False

        for scored in retrieved.items:
            line = self._format_item(scored)
            projected = "\n".join([*lines, line])
            if len(projected) > max_chars:
                trimmed = True
                continue
            lines.append(line)
            included.append(scored)

        if not included:
            first = self._format_item(retrieved.items[0])
            available = max(max_chars - len(lines[0]) - 8, 50)
            lines.append(first[:available])
            included.append(retrieved.items[0])
            trimmed = True

        text = "\n".join(lines)
        logger.debug("Built prompt memory context with %s item(s)", len(included))
        return PromptContext(text=text, included_items=included, trimmed=trimmed)

    def _format_item(self, scored: ScoredContextItem) -> str:
        item = scored.item
        source = item.source.replace("_", " ")
        content = " ".join(item.content.split())
        return f"- [{source} | {item.category} | {scored.score:.1f}] {item.title}: {content}"
