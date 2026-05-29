"""Schemas for deterministic content summaries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SummaryResult:
    """A compact, reusable summary of extracted content."""

    source_text: str
    summary: str
    key_points: tuple[str, ...]
    key_concepts: tuple[str, ...]
    notes: tuple[str, ...]
    word_count: int
