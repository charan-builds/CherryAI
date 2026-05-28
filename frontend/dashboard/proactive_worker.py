"""Background worker for proactive intelligence refreshes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from backend.daily_summary_engine.schemas import DailyProductivitySummary
from backend.memory_consolidation_engine.schemas import ConsolidatedPatternRecord
from backend.observer_engine.schemas import ObserverStatus
from backend.productivity_analyzer.schemas import ProductivityAnalysis
from backend.recommendation_engine.schemas import Recommendation
from backend.semantic_memory_manager.schemas import SemanticMemoryRecord
from backend.service_registry import ServiceRegistry
from backend.working_memory_manager.schemas import WorkingMemoryRecord

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProactiveIntelligenceResult:
    """Data needed to update proactive UI surfaces."""

    analysis: ProductivityAnalysis
    summary: DailyProductivitySummary
    recommendations: list[Recommendation]
    notification_candidates: list[Recommendation]
    semantic_memories: list[SemanticMemoryRecord]
    consolidated_patterns: list[ConsolidatedPatternRecord]
    working_memory: list[WorkingMemoryRecord]


class ProactiveIntelligenceWorker(QThread):
    """Runs deterministic proactive analysis away from the UI thread."""

    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, services: ServiceRegistry, status: ObserverStatus) -> None:
        super().__init__()
        self.services = services
        self.status = status

    def run(self) -> None:
        """Refresh productivity, patterns, summaries, and recommendations."""
        try:
            analysis = self.services.productivity_analyzer.analyze_today()
            insights = self.services.behavioral_patterns.learn_patterns()
            summary = self.services.daily_summaries.generate_from_analysis(analysis)
            recommendations = self.services.recommendations.generate(
                status=self.status,
                analysis=analysis,
                insights=insights,
            )
            notification_candidates = list(recommendations)
            summary_notification = (
                self.services.recommendations.create_daily_summary_notification(summary)
            )
            if summary_notification is not None:
                notification_candidates.append(summary_notification)
            self.services.memory.consolidate()
            semantic_memories = self.services.memory.semantic_memory.list_memories(limit=4)
            consolidated_patterns = (
                self.services.memory.consolidation_engine.list_patterns(limit=4)
            )
            working_memory = self.services.memory.working_memory.list_active()

            self.completed.emit(
                ProactiveIntelligenceResult(
                    analysis=analysis,
                    summary=summary,
                    recommendations=recommendations,
                    notification_candidates=notification_candidates,
                    semantic_memories=semantic_memories,
                    consolidated_patterns=consolidated_patterns,
                    working_memory=working_memory,
                )
            )
        except Exception as exc:
            logger.exception("Proactive intelligence worker failed")
            self.failed.emit(str(exc))
