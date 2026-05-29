"""Deterministic workflow execution engine."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from config.settings import AppSettings
from backend.automation_engine.service import AutomationEngine
from backend.execution_sandbox.service import ExecutionSandbox
from backend.notification_engine.service import NotificationEngine
from backend.observer_engine.service import ObserverEngine
from backend.performance_monitor.service import PerformanceMonitor
from backend.reflection_engine.service import ReflectionEngine
from backend.workflow_execution_engine.step_runner import WorkflowStepRunner
from backend.workflow_state_manager.schemas import (
    CONDITION_ALWAYS,
    CONDITION_CONTEXT_EQUALS,
    CONDITION_PREVIOUS_FAILURE,
    CONDITION_PREVIOUS_SUCCESS,
    STEP_STATUS_CANCELLED,
    STEP_STATUS_COMPLETED,
    STEP_STATUS_FAILED,
    STEP_STATUS_SKIPPED,
    WORKFLOW_STATUS_CANCELLED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WorkflowExecutionResult,
    WorkflowPlan,
    WorkflowStepPlan,
    StepExecutionResult,
)
from backend.workflow_state_manager.service import WorkflowStateManager
from backend.workflow_validator.service import WorkflowValidator


@dataclass
class WorkflowControl:
    """In-memory pause/cancel controls for a running workflow."""

    pause_event: threading.Event = field(default_factory=threading.Event)
    cancel_requested: bool = False

    def __post_init__(self) -> None:
        self.pause_event.set()


@dataclass
class WorkflowExecutionEngine:
    """Executes validated workflows sequentially with retries and controls."""

    settings: AppSettings
    state_manager: WorkflowStateManager
    validator: WorkflowValidator
    automation_engine: AutomationEngine | None = None
    observer_engine: ObserverEngine | None = None
    notification_engine: NotificationEngine | None = None
    reflection_engine: ReflectionEngine | None = None
    step_runner: WorkflowStepRunner | None = None
    execution_sandbox: ExecutionSandbox | None = None
    performance_monitor: PerformanceMonitor | None = None
    controls: dict[str, WorkflowControl] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.step_runner = self.step_runner or WorkflowStepRunner(
            settings=self.settings,
            automation_engine=self.automation_engine,
            observer_engine=self.observer_engine,
            notification_engine=self.notification_engine,
        )

    def execute_plan(self, plan: WorkflowPlan) -> WorkflowExecutionResult:
        """Persist, validate, and execute a workflow plan."""
        workflow = self.state_manager.create_workflow(plan)
        validation = self.validator.validate(plan)
        if not validation.is_valid:
            self.state_manager.fail_workflow(workflow.id, validation.message)
            return WorkflowExecutionResult(
                workflow_id=workflow.id,
                success=False,
                status=WORKFLOW_STATUS_FAILED,
                message=f"Workflow validation failed: {validation.message}",
                step_results=(),
            )
        if self.execution_sandbox is not None:
            safety_score = self.execution_sandbox.score_workflow(
                [
                    {
                        "action_type": step.action_type,
                        "action_name": step.action_name,
                        "parameters": step.parameters,
                    }
                    for step in plan.steps
                ]
            )
            if safety_score <= 0.0 or self.execution_sandbox.emergency_stop:
                reason = "Workflow blocked by execution sandbox."
                self.state_manager.fail_workflow(workflow.id, reason)
                return WorkflowExecutionResult(
                    workflow_id=workflow.id,
                    success=False,
                    status=WORKFLOW_STATUS_FAILED,
                    message=reason,
                    step_results=(),
                )

        return self.execute_existing_plan(plan)

    def execute_existing_plan(self, plan: WorkflowPlan) -> WorkflowExecutionResult:
        """Execute an already persisted plan."""
        workflow_id = plan.id
        control = self.controls.setdefault(workflow_id, WorkflowControl())
        if self.performance_monitor is not None:
            self.performance_monitor.set_workflow_concurrency(len(self.controls))
        step_results: list[StepExecutionResult] = []
        context: dict[str, object] = {}
        previous_result: StepExecutionResult | None = None

        self.state_manager.start_workflow(workflow_id)
        try:
            ordered_steps = sorted(plan.steps, key=lambda step: step.position)
            for index, step in enumerate(ordered_steps):
                if self._cancel_requested(workflow_id):
                    cancelled = self._cancel_step(workflow_id, step.key)
                    step_results.append(cancelled)
                    return self._finish_cancelled(workflow_id, step_results)

                self._wait_if_paused(workflow_id)
                if self._cancel_requested(workflow_id):
                    cancelled = self._cancel_step(workflow_id, step.key)
                    step_results.append(cancelled)
                    return self._finish_cancelled(workflow_id, step_results)

                progress = self._progress(index, len(ordered_steps))
                skip_reason = self._skip_reason(step, step_results, previous_result, context)
                if skip_reason:
                    self.state_manager.mark_step_skipped(
                        workflow_id,
                        step.key,
                        progress,
                        skip_reason,
                    )
                    skipped = StepExecutionResult(
                        step_key=step.key,
                        success=True,
                        status=STEP_STATUS_SKIPPED,
                        message=skip_reason,
                        attempts=0,
                    )
                    step_results.append(skipped)
                    previous_result = skipped
                    continue

                result = self._execute_step_with_retries(
                    workflow_id=workflow_id,
                    step=step,
                    progress_percent=progress,
                )
                step_results.append(result)
                previous_result = result
                context[step.key] = result.data
                context[f"{step.key}.success"] = result.success

                if not result.success and not step.continue_on_failure:
                    self.state_manager.fail_workflow(workflow_id, result.message)
                    return self._reflect(
                        plan,
                        WorkflowExecutionResult(
                            workflow_id=workflow_id,
                            success=False,
                            status=WORKFLOW_STATUS_FAILED,
                            message=result.message,
                            step_results=tuple(step_results),
                        ),
                    )

            self.state_manager.complete_workflow(workflow_id)
            return self._reflect(
                plan,
                WorkflowExecutionResult(
                    workflow_id=workflow_id,
                    success=True,
                    status=WORKFLOW_STATUS_COMPLETED,
                    message="Workflow completed successfully.",
                    step_results=tuple(step_results),
                ),
            )
        finally:
            self.controls.pop(workflow_id, None)
            if self.performance_monitor is not None:
                self.performance_monitor.set_workflow_concurrency(len(self.controls))

    def pause_workflow(self, workflow_id: str) -> None:
        """Pause a running workflow at the next safe checkpoint."""
        control = self.controls.setdefault(workflow_id, WorkflowControl())
        control.pause_event.clear()
        self.state_manager.pause_workflow(workflow_id)

    def resume_workflow(self, workflow_id: str) -> None:
        """Resume a paused workflow."""
        control = self.controls.setdefault(workflow_id, WorkflowControl())
        control.pause_event.set()
        self.state_manager.resume_workflow(workflow_id)

    def cancel_workflow(self, workflow_id: str) -> None:
        """Request cancellation for a running workflow."""
        control = self.controls.setdefault(workflow_id, WorkflowControl())
        control.cancel_requested = True
        control.pause_event.set()
        self.state_manager.cancel_workflow(workflow_id, "Workflow cancellation requested.")

    def _execute_step_with_retries(
        self,
        workflow_id: str,
        step: WorkflowStepPlan,
        progress_percent: float,
    ) -> StepExecutionResult:
        max_retries = min(step.retries, self.settings.workflow_max_retries)
        attempts_allowed = max_retries + 1
        last_result: StepExecutionResult | None = None

        for attempt in range(1, attempts_allowed + 1):
            if self._cancel_requested(workflow_id):
                return self._cancel_step(workflow_id, step.key)

            self.state_manager.mark_step_running(
                workflow_id,
                step.key,
                progress_percent,
                attempt,
            )
            result = self.step_runner.execute_with_timeout(step, attempt)
            last_result = result

            if result.success:
                self.state_manager.mark_step_completed(
                    workflow_id,
                    step.key,
                    self._next_progress(progress_percent, len_step=True),
                    attempt,
                    result.message,
                )
                return result

            self.state_manager.mark_step_failed(
                workflow_id,
                step.key,
                attempt,
                result.error_message or result.message,
            )
            if attempt < attempts_allowed:
                time.sleep(0.15)

        return last_result or StepExecutionResult(
            step_key=step.key,
            success=False,
            status=STEP_STATUS_FAILED,
            message="Step failed without a result.",
        )

    def _skip_reason(
        self,
        step: WorkflowStepPlan,
        completed_results: list[StepExecutionResult],
        previous_result: StepExecutionResult | None,
        context: dict[str, object],
    ) -> str:
        result_by_key = {result.step_key: result for result in completed_results}
        for dependency in step.depends_on:
            dependency_result = result_by_key.get(dependency)
            if dependency_result is None:
                return f"Skipped because dependency '{dependency}' has not run."
            if dependency_result.status != STEP_STATUS_COMPLETED:
                return f"Skipped because dependency '{dependency}' did not complete."

        if step.condition_kind == CONDITION_ALWAYS:
            return ""
        if step.condition_kind == CONDITION_PREVIOUS_SUCCESS:
            return "" if previous_result and previous_result.success else "Previous step did not succeed."
        if step.condition_kind == CONDITION_PREVIOUS_FAILURE:
            return "" if previous_result and not previous_result.success else "Previous step did not fail."
        if step.condition_kind == CONDITION_CONTEXT_EQUALS:
            key = str(step.condition_data.get("key", ""))
            expected = step.condition_data.get("value")
            return "" if context.get(key) == expected else "Workflow condition was not met."
        return "Unknown workflow condition."

    def _wait_if_paused(self, workflow_id: str) -> None:
        control = self.controls.setdefault(workflow_id, WorkflowControl())
        while not control.pause_event.is_set():
            if control.cancel_requested:
                return
            time.sleep(0.1)

    def _cancel_requested(self, workflow_id: str) -> bool:
        control = self.controls.get(workflow_id)
        return bool(control and control.cancel_requested)

    def _cancel_step(self, workflow_id: str, step_key: str) -> StepExecutionResult:
        self.state_manager.mark_step_cancelled(
            workflow_id,
            step_key,
            "Workflow cancellation requested.",
        )
        return StepExecutionResult(
            step_key=step_key,
            success=False,
            status=STEP_STATUS_CANCELLED,
            message="Workflow cancellation requested.",
            attempts=0,
        )

    def _finish_cancelled(
        self,
        workflow_id: str,
        step_results: list[StepExecutionResult],
    ) -> WorkflowExecutionResult:
        self.state_manager.cancel_workflow(workflow_id, "Workflow cancelled.")
        return WorkflowExecutionResult(
            workflow_id=workflow_id,
            success=False,
            status=WORKFLOW_STATUS_CANCELLED,
            message="Workflow cancelled.",
            step_results=tuple(step_results),
        )

    def _reflect(
        self,
        plan: WorkflowPlan,
        result: WorkflowExecutionResult,
    ) -> WorkflowExecutionResult:
        if self.reflection_engine is None:
            return result
        reflection = self.reflection_engine.reflect(plan, result)
        return WorkflowExecutionResult(
            workflow_id=result.workflow_id,
            success=result.success,
            status=result.status,
            message=result.message,
            step_results=result.step_results,
            reflection_summary=reflection.summary,
        )

    def _progress(self, step_index: int, total_steps: int) -> float:
        if total_steps <= 0:
            return 0.0
        return round((step_index / total_steps) * 100, 1)

    def _next_progress(self, progress_percent: float, len_step: bool = True) -> float:
        return min(99.0, progress_percent + (1.0 if len_step else 0.0))
