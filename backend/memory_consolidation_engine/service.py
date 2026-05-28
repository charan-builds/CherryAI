"""Consolidates raw activity into learned memory patterns."""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass

from config.settings import AppSettings
from backend.memory_consolidation_engine.repository import (
    MemoryConsolidationRepository,
    consolidation_since,
)
from backend.memory_consolidation_engine.schemas import (
    ConsolidatedPatternRecord,
    MemoryConsolidationResult,
)
from backend.observer_engine.observer_event_bus.events import DISTRACTION_DETECTED
from backend.semantic_memory_manager.service import SemanticMemoryManager

logger = logging.getLogger(__name__)


@dataclass
class MemoryConsolidationEngine:
    """Turns repeated activity into durable learned insights."""

    settings: AppSettings
    semantic_memory_manager: SemanticMemoryManager
    repository: MemoryConsolidationRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = MemoryConsolidationRepository.from_settings(self.settings)

    def consolidate(self, days: int = 14) -> MemoryConsolidationResult:
        """Run a safe deterministic consolidation pass."""
        since = consolidation_since(days)
        sessions = self.repository.recent_study_sessions(since)
        events = self.repository.recent_events(since)
        summaries = self.repository.recent_summaries(since)

        patterns: list[ConsolidatedPatternRecord] = []
        patterns.extend(self._preferred_productivity_windows(sessions))
        patterns.extend(self._common_distractions(events))
        patterns.extend(self._successful_study_habits(sessions))
        patterns.extend(self._repeated_procrastination(summaries))

        stored_memories = 0
        for pattern in patterns:
            if pattern.confidence < self.settings.semantic_memory_min_confidence:
                continue
            self.semantic_memory_manager.remember(
                text=pattern.insight,
                title=pattern.title,
                source_type="consolidated_pattern",
                source_id=pattern.id,
                importance=0.7,
                confidence=pattern.confidence,
                behavioral_significance=pattern.confidence,
                metadata={
                    "pattern_type": pattern.pattern_type,
                    "evidence_count": pattern.evidence_count,
                },
            )
            stored_memories += 1

        logger.info("Consolidated %s memory pattern(s)", len(patterns))
        return MemoryConsolidationResult(
            patterns=patterns,
            semantic_memories_created=stored_memories,
        )

    def list_patterns(self, limit: int = 20) -> list[ConsolidatedPatternRecord]:
        """Return consolidated learned patterns."""
        return self.repository.list_patterns(limit=limit)

    def _preferred_productivity_windows(self, sessions) -> list[ConsolidatedPatternRecord]:
        productive_hours: Counter[int] = Counter()
        for session in sessions:
            if session.duration_seconds <= 0:
                continue
            focus_ratio = session.focus_seconds / session.duration_seconds
            if focus_ratio >= 0.65:
                productive_hours[session.started_at.hour] += 1

        total = sum(productive_hours.values())
        records: list[ConsolidatedPatternRecord] = []
        for hour, count in productive_hours.most_common(3):
            records.append(
                self.repository.upsert_pattern(
                    pattern_type="preferred_productivity_window",
                    pattern_key=f"hour_{hour:02d}",
                    title=f"Productive around {hour:02d}:00",
                    insight=f"The user tends to have stronger study focus around {hour:02d}:00.",
                    confidence=count / max(total, 1),
                    evidence_count=count,
                    metadata={"hour": hour},
                )
            )
        return records

    def _common_distractions(self, events) -> list[ConsolidatedPatternRecord]:
        counts: Counter[str] = Counter()
        for event in events:
            if event.event_type != DISTRACTION_DETECTED:
                continue
            payload = self._payload(event.payload_json)
            key = str(
                payload.get("keyword")
                or payload.get("application_name")
                or "unknown distraction"
            )
            counts[key] += 1

        total = sum(counts.values())
        records: list[ConsolidatedPatternRecord] = []
        for key, count in counts.most_common(5):
            records.append(
                self.repository.upsert_pattern(
                    pattern_type="common_distraction",
                    pattern_key=key.lower().replace(" ", "_")[:120],
                    title=f"Common distraction: {key}",
                    insight=f"{key} repeatedly appears during focus interruptions.",
                    confidence=count / max(total, 1),
                    evidence_count=count,
                    metadata={"source": key},
                )
            )
        return records

    def _successful_study_habits(self, sessions) -> list[ConsolidatedPatternRecord]:
        strong_sessions = [
            session
            for session in sessions
            if session.duration_seconds >= 25 * 60
            and session.duration_seconds > 0
            and session.focus_seconds / session.duration_seconds >= 0.7
        ]
        if not strong_sessions:
            return []

        return [
            self.repository.upsert_pattern(
                pattern_type="successful_study_habit",
                pattern_key="focused_25_min_blocks",
                title="Successful study habit",
                insight="Focused study blocks of at least 25 minutes tend to work well for the user.",
                confidence=min(len(strong_sessions) / max(len(sessions), 1), 1.0),
                evidence_count=len(strong_sessions),
                metadata={"minimum_minutes": 25},
            )
        ]

    def _repeated_procrastination(self, summaries) -> list[ConsolidatedPatternRecord]:
        quiet_days = [
            summary
            for summary in summaries
            if summary.open_tasks > 0
            and summary.completed_tasks == 0
            and summary.study_duration_seconds == 0
        ]
        if len(quiet_days) < 2:
            return []

        return [
            self.repository.upsert_pattern(
                pattern_type="repeated_procrastination",
                pattern_key="open_tasks_no_progress",
                title="Repeated procrastination risk",
                insight="Open tasks sometimes remain without study progress or completions.",
                confidence=min(len(quiet_days) / max(len(summaries), 1), 1.0),
                evidence_count=len(quiet_days),
                metadata={"days": [item.summary_date.isoformat() for item in quiet_days]},
            )
        ]

    def _payload(self, raw_payload: str) -> dict[str, object]:
        try:
            value = json.loads(raw_payload or "{}")
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}
