"""Deterministic focus scoring."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from backend.focus_scoring_engine.schemas import FocusScoreInput, FocusScoreResult


@dataclass
class FocusScoringEngine:
    """Scores focus sessions using reusable, deterministic rules."""

    settings: AppSettings

    def score(self, score_input: FocusScoreInput) -> FocusScoreResult:
        """Calculate focus duration, interruption rate, severity, and quality."""
        duration = max(score_input.session_duration_seconds, 0.0)
        focus_seconds = max(score_input.focus_duration_seconds, 0.0)
        idle_seconds = max(score_input.idle_seconds, 0.0)
        interruptions = max(score_input.interruption_count, 0)
        distractions = max(score_input.distraction_count, 0)

        focus_ratio = self._safe_ratio(focus_seconds, duration)
        idle_ratio = self._safe_ratio(idle_seconds, duration)
        hours = max(duration / 3600, 0.25)
        interruption_rate = round(interruptions / hours, 2)

        distraction_severity = self._clamp(
            distractions * 16.0 + interruptions * 6.0 + idle_ratio * 20.0
        )

        base_quality = focus_ratio * 100.0
        interruption_penalty = min(interruptions * 5.0, 28.0)
        distraction_penalty = min(distractions * 8.0, 32.0)
        idle_penalty = min(idle_ratio * 30.0, 20.0)
        session_quality = self._clamp(
            base_quality
            - interruption_penalty
            - distraction_penalty
            - idle_penalty
        )

        target_seconds = max(self.settings.focus_target_minutes * 60, 1)
        duration_score = self._clamp((focus_seconds / target_seconds) * 100.0)
        focus_score = self._clamp(session_quality * 0.7 + duration_score * 0.3)

        return FocusScoreResult(
            focus_duration_seconds=round(focus_seconds, 2),
            focus_ratio=round(focus_ratio, 3),
            interruption_rate=interruption_rate,
            distraction_severity=round(distraction_severity, 1),
            session_quality=round(session_quality, 1),
            focus_score=round(focus_score, 1),
        )

    def _safe_ratio(self, numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return min(max(numerator / denominator, 0.0), 1.0)

    def _clamp(self, value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
        return max(min(value, maximum), minimum)
