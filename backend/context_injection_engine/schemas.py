"""Context injection DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from backend.context_retriever.schemas import ScoredContextItem


@dataclass(frozen=True)
class PromptContext:
    """Token-safe context block for prompt injection."""

    text: str
    included_items: list[ScoredContextItem]
    trimmed: bool = False
