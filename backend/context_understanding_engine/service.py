"""Local context classification and semantic tagging."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.context_understanding_engine.schemas import ContextAnalysis


_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "machine_learning": (
        "machine learning",
        "model",
        "neural",
        "regression",
        "classification",
        "dataset",
        "training",
        "accuracy",
        "gradient",
        "probability",
    ),
    "programming": (
        "function",
        "class",
        "import",
        "api",
        "database",
        "architecture",
        "repository",
        "service",
        "pytest",
        "python",
    ),
    "study_material": (
        "chapter",
        "lecture",
        "revision",
        "notes",
        "exam",
        "practice",
        "concept",
        "definition",
    ),
    "productivity": (
        "task",
        "workflow",
        "focus",
        "schedule",
        "deadline",
        "priority",
        "reminder",
    ),
    "user_interface": (
        "button",
        "menu",
        "window",
        "dialog",
        "screen",
        "sidebar",
        "form",
    ),
}


@dataclass
class ContextUnderstandingEngine:
    """Classifies documents, code, screenshots, and study content."""

    min_keyword_confidence: float = 0.35

    def classify(self, text: str, source_type: str = "text") -> ContextAnalysis:
        """Return a deterministic content category and useful tags."""
        normalized = " ".join((text or "").lower().split())
        scores = self._score_categories(normalized)
        category, score = max(scores.items(), key=lambda item: item[1])
        if score == 0 and source_type:
            category = self._category_from_source(source_type)

        topics = self.extract_topics(text)
        tags = self.semantic_tags(text, source_type, category)
        study_topics = self.extract_study_topics(text, category)
        confidence = self._confidence(score, normalized)
        reason = (
            f"Matched {score} keyword(s) for {category}."
            if score
            else f"Used source type '{source_type}' fallback."
        )
        return ContextAnalysis(
            category=category,
            topics=tuple(topics),
            tags=tuple(tags),
            study_topics=tuple(study_topics),
            confidence=confidence,
            reason=reason,
        )

    def categorize(self, text: str, source_type: str = "text") -> str:
        """Return only the top category for simple callers."""
        return self.classify(text, source_type=source_type).category

    def extract_topics(self, text: str, limit: int = 8) -> list[str]:
        """Extract durable topics from phrases and frequent terms."""
        phrases = re.findall(
            r"\b(?:[A-Z][A-Za-z0-9_]+(?:\s+[A-Z][A-Za-z0-9_]+){0,3})\b",
            text or "",
        )
        words = [
            word.lower()
            for word in re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", text or "")
            if word.lower()
            not in {"this", "that", "with", "from", "your", "will", "have"}
        ]
        ordered: list[str] = []
        for value in [*phrases, *words]:
            normalized = " ".join(value.split())
            if normalized.lower() not in {item.lower() for item in ordered}:
                ordered.append(normalized)
            if len(ordered) >= limit:
                break
        return ordered

    def semantic_tags(
        self,
        text: str,
        source_type: str,
        category: str,
    ) -> list[str]:
        """Generate tags that are stable enough for memory retrieval."""
        tags = [source_type, category]
        lowered = (text or "").lower()
        if "deadline" in lowered or "due" in lowered:
            tags.append("time_sensitive")
        if "error" in lowered or "failed" in lowered:
            tags.append("needs_debugging")
        if "example" in lowered or "practice" in lowered:
            tags.append("practice")
        if "summary" in lowered or "notes" in lowered:
            tags.append("notes")
        return list(dict.fromkeys(tag for tag in tags if tag))

    def extract_study_topics(self, text: str, category: str = "") -> list[str]:
        """Extract topics that should appear in a study workspace."""
        if category not in {"machine_learning", "study_material", "programming"}:
            return []
        lowered = (text or "").lower()
        topics: list[str] = []
        known_topics = {
            "probability": "Probability",
            "linear algebra": "Linear Algebra",
            "regression": "Regression",
            "classification": "Classification",
            "neural": "Neural Networks",
            "dataset": "Datasets",
            "python": "Python",
            "architecture": "Architecture",
            "testing": "Testing",
        }
        for needle, label in known_topics.items():
            if needle in lowered and label not in topics:
                topics.append(label)
        return topics

    def _score_categories(self, normalized: str) -> dict[str, int]:
        scores: dict[str, int] = {}
        for category, keywords in _CATEGORY_KEYWORDS.items():
            scores[category] = sum(1 for keyword in keywords if keyword in normalized)
        return scores

    def _category_from_source(self, source_type: str) -> str:
        if source_type in {"code", "project"}:
            return "programming"
        if source_type in {"screenshot", "screen"}:
            return "user_interface"
        if source_type in {"pdf", "document"}:
            return "study_material"
        return "general"

    def _confidence(self, score: int, normalized: str) -> float:
        if not normalized:
            return 0.0
        if score <= 0:
            return self.min_keyword_confidence
        return round(min(0.35 + (score * 0.12), 0.95), 2)
