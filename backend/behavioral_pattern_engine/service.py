"""Behavioral pattern learning."""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass

from config.settings import AppSettings
from backend.behavioral_pattern_engine.repository import (
    BehavioralPatternRepository,
    lookback_start,
)
from backend.behavioral_pattern_engine.schemas import (
    BehavioralInsights,
    BehavioralPatternRecord,
)
from backend.observer_engine.observer_event_bus.events import (
    DISTRACTION_DETECTED,
    FOCUS_LOST,
)

logger = logging.getLogger(__name__)


@dataclass
class BehavioralPatternEngine:
    """Detects and persists local behavior patterns from observed data."""

    settings: AppSettings
    repository: BehavioralPatternRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = BehavioralPatternRepository.from_settings(self.settings)

    def learn_patterns(self, days: int = 14) -> BehavioralInsights:
        """Detect preferred times, distraction windows, productive periods, interruptions."""
        since = lookback_start(days)
        sessions = self.repository.recent_study_sessions(since)
        events = self.repository.recent_events(since)
        learned: list[BehavioralPatternRecord] = []

        learned.extend(self._learn_preferred_study_times(sessions))
        learned.extend(self._learn_productive_periods(sessions))
        learned.extend(self._learn_distraction_windows(events))
        learned.extend(self._learn_common_interruptions(events))

        logger.debug("Learned %s behavioral patterns", len(learned))
        return self.get_insights()

    def get_insights(self) -> BehavioralInsights:
        """Return grouped learned patterns."""
        return BehavioralInsights(
            preferred_study_times=self.repository.list_patterns("preferred_study_time", 3),
            distraction_windows=self.repository.list_patterns("distraction_window", 3),
            productive_periods=self.repository.list_patterns("productive_period", 3),
            common_interruptions=self.repository.list_patterns("common_interruption", 5),
        )

    def _learn_preferred_study_times(self, sessions) -> list[BehavioralPatternRecord]:
        counts = Counter(session.started_at.hour for session in sessions)
        total = sum(counts.values())
        records: list[BehavioralPatternRecord] = []
        if total == 0:
            return records

        for hour, count in counts.most_common(3):
            records.append(
                self.repository.upsert_pattern(
                    pattern_type="preferred_study_time",
                    pattern_key=f"hour_{hour:02d}",
                    description=f"Study often starts around {hour:02d}:00.",
                    confidence=count / total,
                    sample_size=count,
                    metadata={"hour": hour},
                )
            )
        return records

    def _learn_productive_periods(self, sessions) -> list[BehavioralPatternRecord]:
        productive_hours: Counter[int] = Counter()
        for session in sessions:
            if session.duration_seconds <= 0:
                continue
            focus_ratio = session.focus_seconds / session.duration_seconds
            if focus_ratio >= 0.65 and session.interruption_count <= 3:
                productive_hours[session.started_at.hour] += 1

        total = sum(productive_hours.values())
        records: list[BehavioralPatternRecord] = []
        if total == 0:
            return records

        for hour, count in productive_hours.most_common(3):
            records.append(
                self.repository.upsert_pattern(
                    pattern_type="productive_period",
                    pattern_key=f"hour_{hour:02d}",
                    description=f"Focus quality tends to be stronger near {hour:02d}:00.",
                    confidence=count / total,
                    sample_size=count,
                    metadata={"hour": hour},
                )
            )
        return records

    def _learn_distraction_windows(self, events) -> list[BehavioralPatternRecord]:
        counts = Counter(
            event.created_at.hour
            for event in events
            if event.event_type == DISTRACTION_DETECTED
        )
        total = sum(counts.values())
        records: list[BehavioralPatternRecord] = []
        if total == 0:
            return records

        for hour, count in counts.most_common(3):
            records.append(
                self.repository.upsert_pattern(
                    pattern_type="distraction_window",
                    pattern_key=f"hour_{hour:02d}",
                    description=f"Distractions appear more often around {hour:02d}:00.",
                    confidence=count / total,
                    sample_size=count,
                    metadata={"hour": hour},
                )
            )
        return records

    def _learn_common_interruptions(self, events) -> list[BehavioralPatternRecord]:
        counts: Counter[str] = Counter()
        for event in events:
            if event.event_type not in {DISTRACTION_DETECTED, FOCUS_LOST}:
                continue
            payload = self._payload(event.payload_json)
            key = str(
                payload.get("keyword")
                or payload.get("application_name")
                or "unknown interruption"
            )
            counts[key] += 1

        total = sum(counts.values())
        records: list[BehavioralPatternRecord] = []
        if total == 0:
            return records

        for key, count in counts.most_common(5):
            records.append(
                self.repository.upsert_pattern(
                    pattern_type="common_interruption",
                    pattern_key=key.lower().replace(" ", "_")[:120],
                    description=f"{key} commonly interrupts focus.",
                    confidence=count / total,
                    sample_size=count,
                    metadata={"source": key},
                )
            )
        return records

    def _payload(self, raw_payload: str) -> dict[str, object]:
        try:
            value = json.loads(raw_payload or "{}")
        except json.JSONDecodeError:
            return {}
        if isinstance(value, dict):
            return value
        return {}
