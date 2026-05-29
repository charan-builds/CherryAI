"""Routes parsed intents to backend services."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.action_router.schemas import RoutedActionResult
from backend.automation_engine.service import AutomationEngine
from backend.goal_planner_engine.service import GoalPlannerEngine
from backend.intent_parser.schemas import ParsedIntent
from backend.task_engine.service import TaskEngine
from backend.workflow_execution_engine.service import WorkflowExecutionEngine

logger = logging.getLogger(__name__)


@dataclass
class ActionRouter:
    """Executes backend actions for parsed intents."""

    task_engine: TaskEngine
    automation_engine: AutomationEngine | None = None
    goal_planner: GoalPlannerEngine | None = None
    workflow_execution_engine: WorkflowExecutionEngine | None = None
    resume_engine: object | None = None

    def route(self, parsed_intent: ParsedIntent) -> RoutedActionResult:
        """Route an intent to the correct backend service."""
        try:
            if parsed_intent.intent == "start_workflow":
                return self._route_workflow(parsed_intent)

            if parsed_intent.intent == "resume_status":
                return self._route_resume(parsed_intent)

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

            if parsed_intent.intent in {
                "open_app",
                "open_website",
                "play_music",
                "take_screenshot",
                "start_study_workspace",
            }:
                return self._route_automation(parsed_intent)

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

    def _route_automation(self, parsed_intent: ParsedIntent) -> RoutedActionResult:
        if self.automation_engine is None:
            return RoutedActionResult(
                intent=parsed_intent.intent,
                success=False,
                message="Automation engine is not available.",
            )

        tool_name, parameters = self._automation_tool_request(parsed_intent)
        result = self.automation_engine.execute_tool(tool_name, parameters)
        return RoutedActionResult(
            intent=parsed_intent.intent,
            success=result.success,
            message=result.message,
            data={"automation_result": result},
        )

    def _automation_tool_request(
        self,
        parsed_intent: ParsedIntent,
    ) -> tuple[str, dict[str, object]]:
        if parsed_intent.intent == "open_app":
            return "open_app", {"app_name": parsed_intent.app_name or parsed_intent.title}
        if parsed_intent.intent == "open_website":
            return "open_website", {"url": parsed_intent.url or parsed_intent.title}
        if parsed_intent.intent == "play_music":
            playlist_url = str(parsed_intent.raw.get("playlist_url", "")).strip()
            return "play_music", {
                "query": parsed_intent.query or parsed_intent.title or "focus music",
                "playlist_url": playlist_url,
            }
        if parsed_intent.intent == "take_screenshot":
            return "take_screenshot", {}
        if parsed_intent.intent == "start_study_workspace":
            return "open_study_workspace", {
                "topic": parsed_intent.topic or parsed_intent.title or "study",
                "app_name": parsed_intent.app_name or "vscode",
            }
        return parsed_intent.intent, {}

    def _route_workflow(self, parsed_intent: ParsedIntent) -> RoutedActionResult:
        if self.goal_planner is None or self.workflow_execution_engine is None:
            return RoutedActionResult(
                intent=parsed_intent.intent,
                success=False,
                message="Workflow engine is not available.",
            )

        goal = parsed_intent.goal or parsed_intent.title or "Productivity workflow"
        plan = self.goal_planner.create_plan(goal)
        result = self.workflow_execution_engine.execute_plan(plan)
        return RoutedActionResult(
            intent=parsed_intent.intent,
            success=result.success,
            message=result.message,
            data={"workflow_plan": plan, "workflow_result": result},
        )

    def _route_resume(self, parsed_intent: ParsedIntent) -> RoutedActionResult:
        if self.resume_engine is None or not hasattr(
            self.resume_engine,
            "generate_summary",
        ):
            return RoutedActionResult(
                intent=parsed_intent.intent,
                success=False,
                message="Resume engine is not available.",
            )

        summary = self.resume_engine.generate_summary()
        return RoutedActionResult(
            intent=parsed_intent.intent,
            success=True,
            message="Resume summary generated.",
            data={"resume_summary": summary},
        )
