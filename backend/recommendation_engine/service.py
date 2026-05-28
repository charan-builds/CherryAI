"""Contextual proactive recommendation generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from config.settings import AppSettings
from database.models import utc_now
from backend.behavioral_pattern_engine.schemas import BehavioralInsights
from backend.daily_summary_engine.schemas import DailyProductivitySummary
from backend.observer_engine.schemas import ObserverStatus
from backend.ollama_service.service import OllamaGenerationError, OllamaService
from backend.productivity_analyzer.schemas import ProductivityAnalysis
from backend.prompt_manager.service import PromptManager
from backend.recommendation_engine.repository import RecommendationLogRepository
from backend.recommendation_engine.schemas import (
    RECOMMENDATION_CONTINUE_TASK,
    RECOMMENDATION_REDUCE_DISTRACTIONS,
    RECOMMENDATION_RESUME_FOCUS,
    RECOMMENDATION_START_STUDY,
    RECOMMENDATION_TAKE_BREAK,
    Recommendation,
)

logger = logging.getLogger(__name__)


@dataclass
class RecommendationEngine:
    """Generates gentle, cooldown-aware coaching recommendations."""

    settings: AppSettings
    repository: RecommendationLogRepository | None = None
    ollama_service: OllamaService | None = None
    prompt_manager: PromptManager | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = RecommendationLogRepository.from_settings(self.settings)
        self.prompt_manager = self.prompt_manager or PromptManager()

    def generate(
        self,
        status: ObserverStatus,
        analysis: ProductivityAnalysis,
        insights: BehavioralInsights | None = None,
        now: datetime | None = None,
        limit: int = 3,
    ) -> list[Recommendation]:
        """Return contextual recommendations that are not inside cooldown."""
        if not self.settings.proactive_enabled:
            return []

        current_time = now or utc_now()
        candidates = self._build_candidates(status, analysis, insights, current_time)
        allowed: list[Recommendation] = []
        for candidate in candidates:
            if self.repository.has_recent(
                candidate.cooldown_key,
                current_time,
                self.settings.recommendation_cooldown_seconds,
            ):
                continue
            logged = self.repository.create_log(candidate)
            allowed.append(logged)
            if len(allowed) >= limit:
                break

        logger.debug("Generated %s proactive recommendations", len(allowed))
        return allowed

    def contextualize_with_ai(
        self,
        recommendation: Recommendation,
        analysis: ProductivityAnalysis,
    ) -> str:
        """Use Ollama to explain a recommendation without changing metrics."""
        if self.ollama_service is None:
            return recommendation.message

        prompt = self.prompt_manager.get_prompt(
            "recommendation_context",
            recommendation_title=recommendation.title,
            recommendation_message=recommendation.message,
            productivity_score=str(analysis.productivity_score),
            focus_score=str(analysis.focus_score),
            completed_tasks=str(analysis.completed_tasks),
            distractions=str(analysis.distraction_count),
        )
        try:
            return self.ollama_service.generate(prompt)
        except OllamaGenerationError:
            logger.info("Using deterministic recommendation message")
            return recommendation.message

    def create_daily_summary_notification(
        self,
        summary: DailyProductivitySummary,
        now: datetime | None = None,
    ) -> Recommendation | None:
        """Create one low-priority daily summary notification candidate."""
        current_time = now or utc_now()
        if summary.completed_tasks == 0 and summary.study_duration_seconds == 0:
            return None

        cooldown_key = f"daily_summary_{summary.summary_date.isoformat()}"
        if self.repository.has_recent(cooldown_key, current_time, 20 * 3600):
            return None

        recommendation = Recommendation(
            recommendation_type="daily_summary",
            title="Daily summary",
            message=summary.summary_text,
            priority="low",
            cooldown_key=cooldown_key,
            context={
                "summary_date": summary.summary_date.isoformat(),
                "productivity_score": summary.productivity_score,
                "focus_score": summary.focus_score,
            },
            created_at=current_time,
        )
        return self.repository.create_log(recommendation)

    def _build_candidates(
        self,
        status: ObserverStatus,
        analysis: ProductivityAnalysis,
        insights: BehavioralInsights | None,
        now: datetime,
    ) -> list[Recommendation]:
        candidates: list[Recommendation] = []
        in_study = status.active_study_session is not None

        if in_study and status.is_idle:
            candidates.append(
                Recommendation(
                    recommendation_type=RECOMMENDATION_RESUME_FOCUS,
                    title="Resume focus",
                    message="You look paused. A tiny restart is enough: return to the study tab when you are ready.",
                    priority="normal",
                    cooldown_key="resume_focus_idle",
                    context={"idle_seconds": status.idle_seconds},
                    created_at=now,
                )
            )

        if in_study and status.focus_seconds >= self.settings.focus_break_after_minutes * 60:
            candidates.append(
                Recommendation(
                    recommendation_type=RECOMMENDATION_TAKE_BREAK,
                    title="Take a short break",
                    message="Nice sustained focus. A short break now can keep the next stretch cleaner.",
                    priority="normal",
                    cooldown_key="take_break_after_focus",
                    context={"focus_seconds": status.focus_seconds},
                    created_at=now,
                )
            )

        if (
            analysis.distraction_count >= self.settings.distraction_threshold
            or status.distraction_count >= self.settings.distraction_threshold
        ):
            candidates.append(
                Recommendation(
                    recommendation_type=RECOMMENDATION_REDUCE_DISTRACTIONS,
                    title="Reduce distractions",
                    message="Distractions are starting to cluster. Consider closing one noisy tab or app for the next block.",
                    priority="high",
                    cooldown_key="reduce_distractions_cluster",
                    context={
                        "daily_distractions": analysis.distraction_count,
                        "session_distractions": status.distraction_count,
                    },
                    created_at=now,
                )
            )

        if not in_study and analysis.study_duration_seconds == 0 and analysis.open_tasks > 0:
            message = "A focused study block would fit well now."
            if self._current_hour_is_preferred(insights, now):
                message = "This is one of your usual study windows. A short focused block could land well."
            candidates.append(
                Recommendation(
                    recommendation_type=RECOMMENDATION_START_STUDY,
                    title="Start a study session",
                    message=message,
                    priority="normal",
                    cooldown_key="start_study_today",
                    context={
                        "open_tasks": analysis.open_tasks,
                        "study_seconds_today": analysis.study_duration_seconds,
                    },
                    created_at=now,
                )
            )

        if (
            not in_study
            and analysis.open_tasks > 0
            and analysis.completed_tasks == 0
            and analysis.productivity_score < 55
        ):
            candidates.append(
                Recommendation(
                    recommendation_type=RECOMMENDATION_CONTINUE_TASK,
                    title="Continue one task",
                    message="Pick one open task and move it forward for ten minutes. Keep the target small.",
                    priority="low",
                    cooldown_key="continue_open_task",
                    context={"open_tasks": analysis.open_tasks},
                    created_at=now,
                )
            )

        return candidates

    def _current_hour_is_preferred(
        self,
        insights: BehavioralInsights | None,
        now: datetime,
    ) -> bool:
        if insights is None:
            return False
        current_key = f"hour_{now.hour:02d}"
        return any(
            pattern.pattern_key == current_key and pattern.confidence >= 0.25
            for pattern in insights.preferred_study_times
        )
