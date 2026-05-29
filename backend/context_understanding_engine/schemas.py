"""Schemas for local context understanding."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextAnalysis:
    """Classification and semantic tags for a piece of content."""

    category: str
    topics: tuple[str, ...]
    tags: tuple[str, ...]
    study_topics: tuple[str, ...]
    confidence: float
    reason: str
