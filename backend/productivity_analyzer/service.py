"""Deterministic productivity analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from config.settings import AppSettings
from database.models import utc_now
from backend.focus_scoring_engine.schemas import FocusScoreInput
from backend.focus_scoring_engine.service import FocusScoringEngine
from backend.observer_engine.observer_event_bus.events import (
    DISTRACTION_DETECTED,
    FOCUS_LOST,
)
from backend.productivity_analyzer.repository import (
    ProductivityDataRepository,
    day_bounds,
)
from backend.productivity_analyzer.schemas import ProductivityAnalysis

logger = logging.getLogger(__name__)


@dataclass
class ProductivityAnalyzer:
    """Combines task, study, app usage, distraction, and idle metrics."""

    settings: AppSettings
    focus_scoring_engine: FocusScoringEngine
    repository: ProductivityDataRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = ProductivityDataRepository.from_settings(self.settings)

    def analyze_today(self) -> ProductivityAnalysis:
        """Analyze the current UTC day."""
        return self.analyze_day(utc_now().date())

    def analyze_day(self, analysis_date: date) -> ProductivityAnalysis:
        """Build deterministic daily productivity metrics."""
        start, end = day_bounds(analysis_date)
        created_tasks = self.repository.count_created_tasks(start, end)
        completed_tasks = self.repository.count_completed_tasks(start, end)
        open_tasks = self.repository.count_open_tasks()
        study_totals = self.repository.study_totals(start, end)
        app_usage_seconds = self.repository.app_usage_totals(start, end)
        distractions = self.repository.count_events(DISTRACTION_DETECTED, start, end)
        focus_lost = self.repository.count_events(FOCUS_LOST, start, end)
        interruptions = int(study_totals["interruption_count"]) or focus_lost

        focus_metrics = self.focus_scoring_engine.score(
            FocusScoreInput(
                session_duration_seconds=float(study_totals["duration_seconds"]),
                focus_duration_seconds=float(study_totals["focus_seconds"]),
                idle_seconds=float(study_totals["idle_seconds"]),
                interruption_count=interruptions,
                distraction_count=distractions,
            )
        )
        consistency_score = self._consistency_score(analysis_date)
        productivity_score = self._productivity_score(
            completed_tasks=completed_tasks,
            study_seconds=float(study_totals["duration_seconds"]),
            focus_score=focus_metrics.focus_score,
            distraction_count=distractions,
        )

        analysis = ProductivityAnalysis(
            analysis_date=analysis_date,
            created_tasks=created_tasks,
            completed_tasks=completed_tasks,
            open_tasks=open_tasks,
            study_duration_seconds=round(float(study_totals["duration_seconds"]), 2),
            focus_duration_seconds=round(float(study_totals["focus_seconds"]), 2),
            idle_seconds=round(float(study_totals["idle_seconds"]), 2),
            app_usage_seconds=app_usage_seconds,
            distraction_count=distractions,
            interruption_count=interruptions,
            productivity_score=productivity_score,
            consistency_score=consistency_score,
            focus_score=focus_metrics.focus_score,
            focus_metrics=focus_metrics,
        )
        logger.debug("Productivity analysis generated: %s", analysis)
        return analysis

    def _productivity_score(
        self,
        completed_tasks: int,
        study_seconds: float,
        focus_score: float,
        distraction_count: int,
    ) -> float:
        task_target = max(self.settings.productivity_daily_task_target, 1)
        study_target_seconds = max(
            self.settings.productivity_daily_study_target_minutes * 60,
            1,
        )
        task_component = min(completed_tasks / task_target, 1.0) * 35.0
        study_component = min(study_seconds / study_target_seconds, 1.0) * 35.0
        focus_component = min(max(focus_score, 0.0), 100.0) * 0.2
        distraction_component = max(100.0 - distraction_count * 12.0, 0.0) * 0.1
        return round(task_component + study_component + focus_component + distraction_component, 1)

    def _consistency_score(self, analysis_date: date) -> float:
        window_days = 7
        active_days = self.repository.active_days(analysis_date, window_days)
        return round((active_days / window_days) * 100.0, 1)
