"""Natural language response formatting."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.action_router.schemas import RoutedActionResult
from backend.intent_parser.schemas import ParsedIntent
from backend.ollama_service.service import OllamaGenerationError, OllamaService
from backend.prompt_manager.service import PromptManager
from backend.task_engine.schemas import DailyTaskSummary, TaskRecord, TaskStatistics

logger = logging.getLogger(__name__)


@dataclass
class AIResponseHandler:
    """Builds user-facing responses after routing completes."""

    ollama_service: OllamaService
    prompt_manager: PromptManager

    def build_response(
        self,
        user_message: str,
        parsed_intent: ParsedIntent,
        action_result: RoutedActionResult,
        history_text: str,
    ) -> str:
        """Return the final conversational response."""
        if not action_result.success:
            return f"I could not complete that action: {action_result.message}"

        if parsed_intent.intent == "create_task":
            task = action_result.data.get("task")
            if isinstance(task, TaskRecord):
                return f"Done - I added '{task.title}' as a {task.priority} priority task."
            return "Done - I added that task."

        if parsed_intent.intent == "list_tasks":
            tasks = action_result.data.get("tasks", [])
            return self._format_task_list(tasks)

        if parsed_intent.intent == "summarize_tasks":
            return self._format_task_summary(action_result)

        if parsed_intent.intent == "motivational_response":
            return self._ollama_or_fallback(
                prompt_name="motivational_response",
                fallback="Keep the next step small and visible. One focused action is enough to restart momentum.",
                user_message=user_message,
            )

        return self._ollama_or_fallback(
            prompt_name="general_chat",
            fallback=(
                "I am having trouble reaching Ollama right now, but I am still here. "
                "You can ask me to create, list, or summarize tasks locally."
            ),
            user_message=user_message,
            history=history_text,
        )

    def _format_task_list(self, tasks: object) -> str:
        if not isinstance(tasks, list) or not tasks:
            return "You do not have any open tasks right now."

        lines = ["Here are your open tasks:"]
        for index, task in enumerate(tasks, start=1):
            if isinstance(task, TaskRecord):
                lines.append(f"{index}. {task.title} ({task.priority})")
        return "\n".join(lines)

    def _format_task_summary(self, action_result: RoutedActionResult) -> str:
        statistics = action_result.data.get("statistics")
        summary = action_result.data.get("summary")
        if not isinstance(statistics, TaskStatistics) or not isinstance(
            summary,
            DailyTaskSummary,
        ):
            return "I could not build a task summary yet."

        prompt = self.prompt_manager.get_prompt(
            "productivity_summary",
            task_summary=(
                f"{summary.summary_text} Total: {statistics.total}. "
                f"Open: {statistics.open_count}. Completed: {statistics.completed_count}."
            ),
        )

        try:
            return self.ollama_service.generate(prompt)
        except OllamaGenerationError:
            logger.info("Using fallback productivity summary response")
            return (
                f"{summary.summary_text} You have {statistics.open_count} open task(s). "
                "Pick one concrete next action and make it visible."
            )

    def _ollama_or_fallback(
        self,
        prompt_name: str,
        fallback: str,
        **variables: str,
    ) -> str:
        prompt = self.prompt_manager.get_prompt(prompt_name, **variables)
        try:
            return self.ollama_service.generate(prompt)
        except OllamaGenerationError:
            logger.info("Using fallback response for prompt %s", prompt_name)
            return fallback
