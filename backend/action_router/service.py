"""Routes parsed intents to backend services."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.action_router.schemas import RoutedActionResult
from backend.intent_parser.schemas import ParsedIntent
from backend.task_engine.service import TaskEngine

logger = logging.getLogger(__name__)


@dataclass
class ActionRouter:
    """Executes backend actions for parsed intents."""

    task_engine: TaskEngine

    def route(self, parsed_intent: ParsedIntent) -> RoutedActionResult:
        """Route an intent to the correct backend service."""
        try:
            if parsed_intent.intent == "create_task":
                task = self.task_engine.create_task(
                    title=parsed_intent.title,
                    description=parsed_intent.description,
                    priority=parsed_intent.priority,
                )
                return RoutedActionResult(
                    intent=parsed_intent.intent,
                    success=True,
                    message="Task created.",
                    data={"task": task},
                )

            if parsed_intent.intent == "list_tasks":
                tasks = self.task_engine.list_tasks(status_filter="open")
                return RoutedActionResult(
                    intent=parsed_intent.intent,
                    success=True,
                    message="Tasks listed.",
                    data={"tasks": tasks},
                )

            if parsed_intent.intent == "summarize_tasks":
                statistics = self.task_engine.get_statistics()
                summary = self.task_engine.generate_daily_summary()
                return RoutedActionResult(
                    intent=parsed_intent.intent,
                    success=True,
                    message="Task summary generated.",
                    data={"statistics": statistics, "summary": summary},
                )

            return RoutedActionResult(
                intent=parsed_intent.intent,
                success=True,
                message="No backend action required.",
            )
        except Exception as exc:
            logger.exception("Action routing failed for intent %s", parsed_intent.intent)
            return RoutedActionResult(
                intent=parsed_intent.intent,
                success=False,
                message=str(exc),
            )
