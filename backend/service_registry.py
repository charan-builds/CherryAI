"""Composition root for backend engines."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from backend.ai_engine.service import AIEngine
from backend.analytics_engine.service import AnalyticsEngine
from backend.automation_engine.service import AutomationEngine
from backend.behavioral_pattern_engine.service import BehavioralPatternEngine
from backend.daily_summary_engine.service import DailySummaryEngine
from backend.focus_scoring_engine.service import FocusScoringEngine
from backend.memory_engine.service import MemoryEngine
from backend.notification_decision_engine.service import NotificationDecisionEngine
from backend.notification_engine.service import NotificationEngine
from backend.observer_engine.service import ObserverEngine
from backend.planner_engine.service import PlannerEngine
from backend.productivity_analyzer.service import ProductivityAnalyzer
from backend.recommendation_engine.repository import RecommendationLogRepository
from backend.recommendation_engine.service import RecommendationEngine
from backend.task_engine.service import TaskEngine


@dataclass
class ServiceRegistry:
    """Container for long-lived backend services."""

    ai: AIEngine
    planner: PlannerEngine
    automation: AutomationEngine
    observer: ObserverEngine
    analytics: AnalyticsEngine
    memory: MemoryEngine
    notifications: NotificationEngine
    notification_decisions: NotificationDecisionEngine
    focus_scoring: FocusScoringEngine
    productivity_analyzer: ProductivityAnalyzer
    behavioral_patterns: BehavioralPatternEngine
    recommendations: RecommendationEngine
    daily_summaries: DailySummaryEngine
    tasks: TaskEngine


def build_services(settings: AppSettings) -> ServiceRegistry:
    """Instantiate backend engines with shared settings."""
    memory = MemoryEngine(settings=settings)
    analytics = AnalyticsEngine(settings=settings)
    tasks = TaskEngine(settings=settings, analytics_engine=analytics)
    automation = AutomationEngine(settings=settings)
    focus_scoring = FocusScoringEngine(settings=settings)
    productivity_analyzer = ProductivityAnalyzer(
        settings=settings,
        focus_scoring_engine=focus_scoring,
    )
    behavioral_patterns = BehavioralPatternEngine(settings=settings)
    recommendation_logs = RecommendationLogRepository.from_settings(settings)
    ai = AIEngine(
        settings=settings,
        task_engine=tasks,
        automation_engine=automation,
        memory_engine=memory,
    )
    recommendations = RecommendationEngine(
        settings=settings,
        repository=recommendation_logs,
        ollama_service=ai.ollama_service,
        prompt_manager=ai.prompt_manager,
    )
    daily_summaries = DailySummaryEngine(
        settings=settings,
        productivity_analyzer=productivity_analyzer,
        ollama_service=ai.ollama_service,
        prompt_manager=ai.prompt_manager,
    )

    return ServiceRegistry(
        ai=ai,
        planner=PlannerEngine(settings=settings, ai_engine=ai, memory_engine=memory),
        automation=automation,
        observer=ObserverEngine(settings=settings),
        analytics=analytics,
        memory=memory,
        notifications=NotificationEngine(settings=settings),
        notification_decisions=NotificationDecisionEngine(
            settings=settings,
            repository=recommendation_logs,
        ),
        focus_scoring=focus_scoring,
        productivity_analyzer=productivity_analyzer,
        behavioral_patterns=behavioral_patterns,
        recommendations=recommendations,
        daily_summaries=daily_summaries,
        tasks=tasks,
    )
