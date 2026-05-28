"""Daily productivity summary generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from config.settings import AppSettings
from database.models import utc_now
from backend.daily_summary_engine.repository import DailySummaryRepository
from backend.daily_summary_engine.schemas import DailyProductivitySummary
from backend.ollama_service.service import OllamaGenerationError, OllamaService
from backend.productivity_analyzer.schemas import ProductivityAnalysis
from backend.productivity_analyzer.service import ProductivityAnalyzer
from backend.prompt_manager.service import PromptManager

logger = logging.getLogger(__name__)


@dataclass
class DailySummaryEngine:
    """Generates and persists deterministic daily productivity summaries."""

    settings: AppSettings
    productivity_analyzer: ProductivityAnalyzer
    repository: DailySummaryRepository | None = None
    ollama_service: OllamaService | None = None
    prompt_manager: PromptManager | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = DailySummaryRepository.from_settings(self.settings)
        self.prompt_manager = self.prompt_manager or PromptManager()

    def generate_today(self, include_ai_insight: bool = False) -> DailyProductivitySummary:
        """Generate today's daily summary."""
        return self.generate_for_day(utc_now().date(), include_ai_insight)

    def generate_for_day(
        self,
        summary_date: date,
        include_ai_insight: bool = False,
    ) -> DailyProductivitySummary:
        """Generate, persist, and return a daily summary."""
        analysis = self.productivity_analyzer.analyze_day(summary_date)
        summary = self.from_analysis(analysis)
        if include_ai_insight:
            summary = self.with_ai_insight(summary, analysis)
        stored = self.repository.upsert(summary)
        logger.debug("Daily productivity summary stored for %s", summary_date)
        return stored

    def generate_from_analysis(
        self,
        analysis: ProductivityAnalysis,
        include_ai_insight: bool = False,
    ) -> DailyProductivitySummary:
        """Persist a summary from a precomputed productivity analysis."""
        summary = self.from_analysis(analysis)
        if include_ai_insight:
            summary = self.with_ai_insight(summary, analysis)
        return self.repository.upsert(summary)

    def from_analysis(self, analysis: ProductivityAnalysis) -> DailyProductivitySummary:
        """Build a deterministic summary from already-calculated metrics."""
        study_minutes = int(analysis.study_duration_seconds // 60)
        focus_minutes = int(analysis.focus_duration_seconds // 60)
        summary_text = (
            f"Productivity score {analysis.productivity_score}/100. "
            f"You completed {analysis.completed_tasks} task(s) and studied for {study_minutes} min."
        )
        focus_report = (
            f"Focus score {analysis.focus_score}/100 with {focus_minutes} focused min, "
            f"{analysis.interruption_count} interruption(s), and "
            f"{analysis.distraction_count} distraction(s)."
        )
        task_report = (
            f"{analysis.completed_tasks} completed, {analysis.created_tasks} created, "
            f"{analysis.open_tasks} still open."
        )
        study_statistics = {
            "study_minutes": study_minutes,
            "focus_minutes": focus_minutes,
            "idle_seconds": analysis.idle_seconds,
            "top_apps": list(analysis.app_usage_seconds.items())[:5],
            "consistency_score": analysis.consistency_score,
        }
        return DailyProductivitySummary(
            summary_date=analysis.analysis_date,
            productivity_score=analysis.productivity_score,
            consistency_score=analysis.consistency_score,
            focus_score=analysis.focus_score,
            completed_tasks=analysis.completed_tasks,
            open_tasks=analysis.open_tasks,
            study_duration_seconds=analysis.study_duration_seconds,
            focus_duration_seconds=analysis.focus_duration_seconds,
            distraction_count=analysis.distraction_count,
            interruption_count=analysis.interruption_count,
            summary_text=summary_text,
            focus_report=focus_report,
            task_report=task_report,
            study_statistics=study_statistics,
        )

    def with_ai_insight(
        self,
        summary: DailyProductivitySummary,
        analysis: ProductivityAnalysis,
    ) -> DailyProductivitySummary:
        """Ask Ollama to interpret the deterministic summary without recalculating."""
        if self.ollama_service is None:
            return summary

        prompt = self.prompt_manager.get_prompt(
            "daily_productivity_insight",
            summary_text=summary.summary_text,
            focus_report=summary.focus_report,
            task_report=summary.task_report,
            productivity_score=str(analysis.productivity_score),
            focus_score=str(analysis.focus_score),
        )
        try:
            ai_insight = self.ollama_service.generate(prompt)
        except OllamaGenerationError:
            logger.info("Using summary without AI insight")
            ai_insight = ""

        return DailyProductivitySummary(
            summary_date=summary.summary_date,
            productivity_score=summary.productivity_score,
            consistency_score=summary.consistency_score,
            focus_score=summary.focus_score,
            completed_tasks=summary.completed_tasks,
            open_tasks=summary.open_tasks,
            study_duration_seconds=summary.study_duration_seconds,
            focus_duration_seconds=summary.focus_duration_seconds,
            distraction_count=summary.distraction_count,
            interruption_count=summary.interruption_count,
            summary_text=summary.summary_text,
            focus_report=summary.focus_report,
            task_report=summary.task_report,
            study_statistics=summary.study_statistics,
            ai_insight=ai_insight,
        )
