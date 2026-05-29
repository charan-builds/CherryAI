"""Workflow reflection engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.ollama_service.service import OllamaGenerationError, OllamaService
from backend.reflection_engine.schemas import WorkflowReflection
from backend.workflow_memory_manager.service import WorkflowMemoryManager
from backend.workflow_state_manager.schemas import WorkflowExecutionResult, WorkflowPlan

logger = logging.getLogger(__name__)


@dataclass
class ReflectionEngine:
    """Analyzes workflow outcomes and updates workflow memory."""

    settings: AppSettings
    workflow_memory: WorkflowMemoryManager | None = None
    ollama_service: OllamaService | None = None

    def reflect(
        self,
        plan: WorkflowPlan,
        result: WorkflowExecutionResult,
    ) -> WorkflowReflection:
        """Analyze one completed workflow execution."""
        failed_steps = tuple(
            step.step_key for step in result.step_results if not step.success
        )
        suggestions = self._suggest_retries(plan, result)
        summary = self._build_summary(plan, result, failed_steps, suggestions)

        reflection = WorkflowReflection(
            workflow_id=result.workflow_id,
            success=result.success,
            summary=summary,
            failed_steps=failed_steps,
            retry_suggestions=tuple(suggestions),
        )
        if self.workflow_memory is not None:
            self.workflow_memory.remember_execution(plan, result, summary)
        return reflection

    def summarize_execution(self, result: WorkflowExecutionResult) -> str:
        """Summarize execution with Ollama when available."""
        fallback = result.reflection_summary or result.message
        if self.ollama_service is None:
            return fallback

        prompt = (
            "Summarize this Cherry AI workflow execution in two sentences.\n"
            f"Status: {result.status}\n"
            f"Message: {result.message}\n"
            f"Steps: {[(step.step_key, step.status, step.message) for step in result.step_results]}"
        )
        try:
            return self.ollama_service.generate(prompt)
        except OllamaGenerationError:
            return fallback

    def _build_summary(
        self,
        plan: WorkflowPlan,
        result: WorkflowExecutionResult,
        failed_steps: tuple[str, ...],
        suggestions: list[str],
    ) -> str:
        if result.success:
            return f"Workflow completed successfully: {plan.name}."
        if failed_steps:
            return (
                f"Workflow failed after step(s): {', '.join(failed_steps)}. "
                f"{suggestions[0] if suggestions else 'Review the failed step and retry.'}"
            )
        return f"Workflow ended with status {result.status}: {result.message}"

    def _suggest_retries(
        self,
        plan: WorkflowPlan,
        result: WorkflowExecutionResult,
    ) -> list[str]:
        step_lookup = {step.key: step for step in plan.steps}
        suggestions: list[str] = []
        for step_result in result.step_results:
            if step_result.success:
                continue
            plan_step = step_lookup.get(step_result.step_key)
            if plan_step is None:
                suggestions.append("Retry after refreshing the workflow plan.")
                continue
            if plan_step.action_type == "automation_tool":
                suggestions.append(
                    f"Retry '{plan_step.name}' after checking the app, URL, or permission state."
                )
            elif plan_step.action_type == "study_session":
                suggestions.append(
                    f"Retry '{plan_step.name}' after checking Study Mode availability."
                )
            else:
                suggestions.append(f"Retry '{plan_step.name}' when ready.")
        return suggestions
