"""Contextual companion recommendation engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from config.settings import AppSettings
from database.models import utc_now
from backend.contextual_recommendation_engine.schemas import (
    ContextualRecommendation,
)
from backend.productivity_analyzer.service import ProductivityAnalyzer
from backend.task_engine.service import TaskEngine
from backend.workflow_memory_manager.service import WorkflowMemoryManager
from backend.workflow_state_manager.service import WorkflowStateManager


@dataclass
class ContextualRecommendationEngine:
    """Generates personalized recommendations from local context."""

    settings: AppSettings
    task_engine: TaskEngine
    productivity_analyzer: ProductivityAnalyzer
    workflow_memory: WorkflowMemoryManager | None = None
    workflow_state: WorkflowStateManager | None = None

    def generate(self, limit: int = 4) -> list[ContextualRecommendation]:
        """Return deterministic contextual recommendations."""
        today = utc_now().date()
        analysis = self.productivity_analyzer.analyze_day(today)
        yesterday = self.productivity_analyzer.analyze_day(today - timedelta(days=1))
        open_tasks = self.task_engine.list_tasks(status_filter="open")
        recommendations: list[ContextualRecommendation] = []

        if open_tasks and analysis.completed_tasks == 0:
            task = open_tasks[0]
            recommendations.append(
                ContextualRecommendation(
                    title="Start with one visible task",
                    message=f"You have not completed a task yet today. Try '{task.title}' for 25 minutes.",
                    reason="Open tasks are waiting and today's completion count is zero.",
                    priority="normal",
                    cooldown_key="start_visible_task",
                    context={"task_id": task.id},
                )
            )

        if analysis.distraction_count >= self.settings.distraction_threshold:
            recommendations.append(
                ContextualRecommendation(
                    title="Protect the next focus block",
                    message="Distractions are clustering. Close one noisy app before the next block.",
                    reason="Daily distraction count is above your configured threshold.",
                    priority="high",
                    cooldown_key="protect_focus_block",
                )
            )

        if analysis.study_duration_seconds == 0 and yesterday.study_duration_seconds == 0:
            recommendations.append(
                ContextualRecommendation(
                    title="Return to study rhythm",
                    message="You have not logged study time for two days. A short ML block would restart the rhythm.",
                    reason="No study session was recorded today or yesterday.",
                    priority="normal",
                    cooldown_key="study_gap_two_days",
                )
            )

        memory_recommendation = self._memory_recommendation()
        if memory_recommendation is not None:
            recommendations.append(memory_recommendation)

        return recommendations[:limit]

    def _memory_recommendation(self) -> ContextualRecommendation | None:
        if self.workflow_memory is None:
            return None
        patterns = self.workflow_memory.list_patterns(limit=5)
        for pattern in patterns:
            if pattern.get("preferred"):
                return ContextualRecommendation(
                    title="Reuse a workflow that worked",
                    message=f"'{pattern['workflow_name']}' has worked before. You can launch it again when ready.",
                    reason="Workflow memory marked this pattern as preferred.",
                    priority="low",
                    cooldown_key="reuse_preferred_workflow",
                    context={"goal_signature": pattern["goal_signature"]},
                )
        return None
