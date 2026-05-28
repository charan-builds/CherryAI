"""Composition root for backend engines."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from backend.ai_engine.service import AIEngine
from backend.analytics_engine.service import AnalyticsEngine
from backend.automation_engine.service import AutomationEngine
from backend.memory_engine.service import MemoryEngine
from backend.notification_engine.service import NotificationEngine
from backend.observer_engine.service import ObserverEngine
from backend.planner_engine.service import PlannerEngine
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
    tasks: TaskEngine


def build_services(settings: AppSettings) -> ServiceRegistry:
    """Instantiate backend engines with shared settings."""
    ai = AIEngine(settings=settings)
    memory = MemoryEngine(settings=settings)
    analytics = AnalyticsEngine(settings=settings)
    tasks = TaskEngine(settings=settings, analytics_engine=analytics)

    return ServiceRegistry(
        ai=ai,
        planner=PlannerEngine(settings=settings, ai_engine=ai, memory_engine=memory),
        automation=AutomationEngine(settings=settings),
        observer=ObserverEngine(settings=settings),
        analytics=analytics,
        memory=memory,
        notifications=NotificationEngine(settings=settings),
        tasks=tasks,
    )
