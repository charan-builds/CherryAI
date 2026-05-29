"""Daily reflection engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from config.settings import AppSettings
from database.models import utc_now
from backend.daily_reflection_engine.schemas import DailyReflection
from backend.productivity_analyzer.service import ProductivityAnalyzer
from backend.recommendation_engine.repository import RecommendationLogRepository


@dataclass
class DailyReflectionEngine:
    """Generates end-of-day reflection cards."""

    settings: AppSettings
    productivity_analyzer: ProductivityAnalyzer
    recommendation_repository: RecommendationLogRepository | None = None

    def __post_init__(self) -> None:
        self.recommendation_repository = (
            self.recommendation_repository
            or RecommendationLogRepository.from_settings(self.settings)
        )

    def generate(self, reflection_date: date | None = None) -> DailyReflection:
        """Generate deterministic reflection metrics for one day."""
        day = reflection_date or utc_now().date()
        analysis = self.productivity_analyzer.analyze_day(day)
        effectiveness = self._recommendation_effectiveness()
        study_minutes = int(analysis.study_duration_seconds // 60)
        summary = (
            f"You studied for {study_minutes} min, completed "
            f"{analysis.completed_tasks} task(s), and had "
            f"{analysis.distraction_count} distraction(s)."
        )
        return DailyReflection(
            reflection_date=day,
            study_duration_minutes=study_minutes,
            focus_score=analysis.focus_score,
            distractions=analysis.distraction_count,
            completed_tasks=analysis.completed_tasks,
            recommendation_effectiveness=effectiveness,
            summary_text=summary,
            card_items=(
                f"Study: {study_minutes} min",
                f"Focus: {analysis.focus_score}/100",
                f"Tasks: {analysis.completed_tasks} completed",
                f"Distractions: {analysis.distraction_count}",
            ),
        )

    def _recommendation_effectiveness(self) -> float:
        generated = self.recommendation_repository.count_logs()
        if generated == 0:
            return 0.0
        delivered = self.recommendation_repository.count_logs(status="delivered")
        return round((delivered / generated) * 100.0, 1)
