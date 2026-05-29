"""Deterministic extractive summarization for local knowledge content."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from backend.content_summarization_engine.schemas import SummaryResult


_STOP_WORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "before",
    "being",
    "between",
    "could",
    "every",
    "from",
    "have",
    "into",
    "more",
    "most",
    "only",
    "other",
    "should",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "through",
    "using",
    "were",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
}


@dataclass
class ContentSummarizationEngine:
    """Creates beginner-readable summaries without relying on an LLM."""

    max_summary_sentences: int = 3
    max_key_points: int = 5
    max_concepts: int = 8

    def summarize(
        self,
        text: str,
        max_sentences: int | None = None,
    ) -> SummaryResult:
        """Return an extractive summary, notes, and key concepts."""
        cleaned = self._normalize_text(text)
        sentences = self._split_sentences(cleaned)
        word_count = len(re.findall(r"[A-Za-z0-9_]+", cleaned))
        concepts = self.extract_key_concepts(cleaned, limit=self.max_concepts)
        sentence_limit = max_sentences or self.max_summary_sentences
        summary_sentences = self._rank_sentences(sentences, concepts, sentence_limit)
        key_points = tuple(summary_sentences[: self.max_key_points])

        if not summary_sentences and cleaned:
            summary_sentences = [cleaned[:240]]
        summary = " ".join(summary_sentences).strip()

        return SummaryResult(
            source_text=cleaned,
            summary=summary or "No readable content was found.",
            key_points=key_points,
            key_concepts=tuple(concepts),
            notes=self.create_notes(key_points, concepts),
            word_count=word_count,
        )

    def extract_key_concepts(self, text: str, limit: int = 8) -> list[str]:
        """Extract important terms using frequencies and capitalized phrases."""
        cleaned = self._normalize_text(text)
        capitalized_phrases = re.findall(
            r"\b(?:[A-Z][A-Za-z0-9_]+(?:\s+[A-Z][A-Za-z0-9_]+){0,3})\b",
            cleaned,
        )
        words = [
            word.lower()
            for word in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", cleaned)
            if word.lower() not in _STOP_WORDS
        ]
        counts = Counter(words)

        concepts: list[str] = []
        for phrase in capitalized_phrases:
            normalized = " ".join(phrase.split())
            if normalized.lower() not in _STOP_WORDS:
                self._append_unique(concepts, normalized)
            if len(concepts) >= limit:
                return concepts

        for word, _ in counts.most_common(limit * 2):
            self._append_unique(concepts, word)
            if len(concepts) >= limit:
                break
        return concepts

    def create_notes(
        self,
        key_points: tuple[str, ...],
        concepts: list[str],
    ) -> tuple[str, ...]:
        """Create short study notes from summary points and concepts."""
        notes = [point.strip() for point in key_points if point.strip()]
        if concepts:
            notes.append("Key concepts: " + ", ".join(concepts[:6]))
        return tuple(notes[: self.max_key_points + 1])

    def _rank_sentences(
        self,
        sentences: list[str],
        concepts: list[str],
        limit: int,
    ) -> list[str]:
        if not sentences:
            return []

        concept_set = {concept.lower() for concept in concepts}
        scored: list[tuple[float, int, str]] = []
        for index, sentence in enumerate(sentences):
            words = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", sentence.lower())
            if not words:
                continue
            concept_hits = sum(1 for word in words if word in concept_set)
            length_score = min(len(words), 28) / 28
            early_bonus = 1.0 if index < 3 else 0.0
            score = concept_hits + length_score + early_bonus
            scored.append((score, index, sentence))

        selected = sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]
        return [sentence for _, _, sentence in sorted(selected, key=lambda item: item[1])]

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [part.strip() for part in parts if len(part.strip()) > 20]

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _append_unique(self, items: list[str], value: str) -> None:
        if not value:
            return
        normalized = value.strip()
        existing = {item.lower() for item in items}
        if normalized.lower() not in existing:
            items.append(normalized)
