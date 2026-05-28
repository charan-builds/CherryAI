"""Deterministic memory classification."""

from __future__ import annotations

from dataclasses import dataclass

from backend.memory_classifier.schemas import (
    MEMORY_BEHAVIORAL,
    MEMORY_EPISODIC,
    MEMORY_SEMANTIC,
    MEMORY_WORKING,
    MemoryClassificationInput,
    MemoryClassificationResult,
)


@dataclass
class MemoryClassifier:
    """Classifies memory signals into episodic, behavioral, semantic, or working."""

    def classify(
        self,
        memory_input: MemoryClassificationInput | str,
    ) -> MemoryClassificationResult:
        """Classify text using source-aware deterministic heuristics."""
        if isinstance(memory_input, str):
            memory_input = MemoryClassificationInput(text=memory_input)

        text = memory_input.text.strip()
        normalized = text.lower()
        source_type = memory_input.source_type.lower()

        if source_type in {"working_state", "active_session"} or any(
            phrase in normalized
            for phrase in ("current ", "active ", "right now", "temporary")
        ):
            return MemoryClassificationResult(
                category=MEMORY_WORKING,
                confidence=0.88,
                reason="Current or temporary context belongs in working memory.",
                importance_hint=0.45,
            )

        if source_type in {"study_session", "task_completion"} or any(
            phrase in normalized
            for phrase in ("completed study", "finished", "completed task", "session")
        ):
            return MemoryClassificationResult(
                category=MEMORY_EPISODIC,
                confidence=0.82,
                reason="The signal describes a concrete event.",
                importance_hint=0.55,
            )

        if source_type in {"behavioral_pattern", "productivity_summary"} or any(
            phrase in normalized
            for phrase in (
                "loses focus",
                "distraction",
                "procrastination",
                "interruption",
                "after 45 minutes",
                "pattern",
                "habit",
            )
        ):
            return MemoryClassificationResult(
                category=MEMORY_BEHAVIORAL,
                confidence=0.84,
                reason="The signal describes repeated behavior or focus dynamics.",
                importance_hint=0.7,
            )

        if any(
            phrase in normalized
            for phrase in (
                "prefers",
                "preference",
                "likes",
                "usually studies",
                "best at",
                "works well",
            )
        ):
            return MemoryClassificationResult(
                category=MEMORY_SEMANTIC,
                confidence=0.8,
                reason="The signal describes a stable preference or fact.",
                importance_hint=0.65,
            )

        return MemoryClassificationResult(
            category=MEMORY_SEMANTIC,
            confidence=0.5,
            reason="Defaulting to general learned knowledge.",
            importance_hint=0.4,
        )
