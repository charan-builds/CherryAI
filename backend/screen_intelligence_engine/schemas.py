"""Schemas for screenshot understanding."""

from __future__ import annotations

from dataclasses import dataclass

from backend.context_understanding_engine.schemas import ContextAnalysis


@dataclass(frozen=True)
class ScreenAnalysis:
    """OCR and explanation for a screenshot."""

    image_path: str
    extracted_text: str
    explanation: str
    ui_elements: tuple[str, ...]
    study_explanation: str
    context: ContextAnalysis
