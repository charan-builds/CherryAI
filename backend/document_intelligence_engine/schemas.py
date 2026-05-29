"""Schemas for document understanding."""

from __future__ import annotations

from dataclasses import dataclass

from backend.content_summarization_engine.schemas import SummaryResult
from backend.context_understanding_engine.schemas import ContextAnalysis


@dataclass(frozen=True)
class DocumentAnalysis:
    """Parsed and understood document content."""

    document_path: str
    title: str
    text: str
    summary: SummaryResult
    context: ContextAnalysis
    notes: tuple[str, ...]
    key_concepts: tuple[str, ...]
    page_count: int
