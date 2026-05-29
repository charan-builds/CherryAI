"""Startup briefing engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from config.settings import AppSettings
from database.models import utc_now
from backend.daily_summary_engine.service import DailySummaryEngine
from backend.productivity_analyzer.service import ProductivityAnalyzer
from backend.startup_briefing_engine.schemas import StartupBriefing
from backend.task_engine.service import TaskEngine
from backend.workflow_state_manager.service import WorkflowStateManager


@dataclass
class StartupBriefingEngine:
    """Builds the daily startup briefing from local context."""

    settings: AppSettings
    task_engine: TaskEngine
    daily_summary_engine: DailySummaryEngine
    productivity_analyzer: ProductivityAnalyzer
    workflow_state: WorkflowStateManager | None = None

    def generate(self) -> StartupBriefing:
        """Generate a deterministic startup briefing."""
        now = utc_now()
        yesterday = now.date() - timedelta(days=1)
        today_analysis = self.productivity_analyzer.analyze_today()
        yesterday_summary = self.daily_summary_engine.generate_for_day(yesterday)
        pending_tasks = self.task_engine.list_tasks(status_filter="open")[:5]
        active_goals = self._active_goals()
        suggested = self._suggest_first_action([task.title for task in pending_tasks])

        return StartupBriefing(
            greeting=self._greeting(now.hour),
            pending_tasks=tuple(task.title for task in pending_tasks),
            active_goals=tuple(active_goals),
            focus_score_trend=self._focus_trend(
                today_analysis.focus_score,
                yesterday_summary.focus_score,
            ),
            yesterday_summary=(
                f"Yesterday: {yesterday_summary.completed_tasks} task(s), "
                f"focus score {yesterday_summary.focus_score}/100, "
                f"{int(yesterday_summary.study_duration_seconds // 60)} study min."
            ),
            suggested_first_action=suggested,
            generated_at=now,
        )

    def _greeting(self, hour: int) -> str:
        if hour < 12:
            prefix = "Good morning"
        elif hour < 17:
            prefix = "Good afternoon"
        else:
            prefix = "Good evening"
        return f"{prefix} {self.settings.user_display_name}."

    def _active_goals(self) -> list[str]:
        if self.workflow_state is None:
            return []
        return [
            workflow.goal
            for workflow in self.workflow_state.list_active_workflows(limit=3)
        ]

    def _focus_trend(self, today_score: float, yesterday_score: float) -> str:
        delta = round(today_score - yesterday_score, 1)
        if abs(delta) < 1:
            return "Focus trend is steady."
        direction = "up" if delta > 0 else "down"
        return f"Focus trend is {direction} {abs(delta)}/100 from yesterday."

    def _suggest_first_action(self, pending_task_titles: list[str]) -> str:
        if pending_task_titles:
            return f"Start with {pending_task_titles[0]} for 30 minutes."
        return "Start a short focus block and capture the first task that matters."
