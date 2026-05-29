"""Step action runner for workflow execution."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass

from config.settings import AppSettings
from database.models import utc_now
from backend.automation_engine.schemas import AutomationResult
from backend.automation_engine.service import AutomationEngine
from backend.notification_engine.service import NotificationEngine
from backend.observer_engine.service import ObserverEngine
from backend.workflow_state_manager.schemas import (
    ACTION_TYPE_AUTOMATION,
    ACTION_TYPE_NOOP,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_STUDY_SESSION,
    STEP_STATUS_COMPLETED,
    STEP_STATUS_FAILED,
    WorkflowStepPlan,
    StepExecutionResult,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStepRunner:
    """Executes one workflow step with deterministic action handlers."""

    settings: AppSettings
    automation_engine: AutomationEngine | None = None
    observer_engine: ObserverEngine | None = None
    notification_engine: NotificationEngine | None = None

    def execute_with_timeout(
        self,
        step: WorkflowStepPlan,
        attempt: int,
    ) -> StepExecutionResult:
        """Execute a step and return a timeout failure if it runs too long."""
        timeout_seconds = step.timeout_seconds or self.settings.workflow_step_timeout_seconds
        started_at = utc_now()
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._execute_action, step, attempt, started_at)
        try:
            return future.result(timeout=timeout_seconds)
        except TimeoutError:
            future.cancel()
            return StepExecutionResult(
                step_key=step.key,
                success=False,
                status=STEP_STATUS_FAILED,
                message=f"Step timed out after {timeout_seconds:.1f}s.",
                attempts=attempt,
                error_message="Workflow step timed out.",
                started_at=started_at,
                completed_at=utc_now(),
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _execute_action(
        self,
        step: WorkflowStepPlan,
        attempt: int,
        started_at,
    ) -> StepExecutionResult:
        try:
            if step.action_type == ACTION_TYPE_AUTOMATION:
                return self._execute_automation_step(step, attempt, started_at)
            if step.action_type == ACTION_TYPE_STUDY_SESSION:
                return self._execute_study_step(step, attempt, started_at)
            if step.action_type == ACTION_TYPE_NOTIFICATION:
                return self._execute_notification_step(step, attempt, started_at)
            if step.action_type == ACTION_TYPE_NOOP:
                message = str(step.parameters.get("message", step.name))
                return self._success(step, attempt, message, {}, started_at)
            return self._failure(
                step,
                attempt,
                f"Unsupported action type: {step.action_type}",
                started_at,
            )
        except Exception as exc:
            logger.exception("Workflow step execution failed: %s", step.key)
            return self._failure(step, attempt, str(exc), started_at)

    def _execute_automation_step(
        self,
        step: WorkflowStepPlan,
        attempt: int,
        started_at,
    ) -> StepExecutionResult:
        if self.automation_engine is None:
            return self._failure(
                step,
                attempt,
                "Automation engine is unavailable.",
                started_at,
            )

        tool_name = str(step.parameters.get("tool_name", ""))
        parameters = dict(step.parameters.get("parameters", {}) or {})
        confirmed = bool(step.parameters.get("confirmed", False))
        result: AutomationResult = self.automation_engine.execute_tool(
            tool_name,
            parameters,
            confirmed=confirmed,
        )
        if result.success:
            return self._success(
                step,
                attempt,
                result.message,
                {"automation_action_id": result.action_id, **result.data},
                started_at,
            )
        return self._failure(
            step,
            attempt,
            result.error_message or result.message,
            started_at,
            data={"confirmation_required": result.confirmation_required},
        )

    def _execute_study_step(
        self,
        step: WorkflowStepPlan,
        attempt: int,
        started_at,
    ) -> StepExecutionResult:
        if self.observer_engine is None:
            return self._failure(
                step,
                attempt,
                "Observer engine is unavailable.",
                started_at,
            )

        if step.action_name == "start":
            topic = str(step.parameters.get("topic", "Focused study"))
            session = self.observer_engine.start_study_session(topic)
            return self._success(
                step,
                attempt,
                f"Study Mode started: {session.topic}",
                {"study_session_id": session.id, "topic": session.topic},
                started_at,
            )
        if step.action_name == "stop":
            session = self.observer_engine.stop_study_session()
            return self._success(
                step,
                attempt,
                "Study Mode stopped.",
                {"study_session_id": session.id if session else ""},
                started_at,
            )
        return self._failure(step, attempt, "Unknown Study Mode action.", started_at)

    def _execute_notification_step(
        self,
        step: WorkflowStepPlan,
        attempt: int,
        started_at,
    ) -> StepExecutionResult:
        message = str(step.parameters.get("message", step.name))
        if self.notification_engine is not None:
            self.notification_engine.notify(message)
        return self._success(step, attempt, message, {"message": message}, started_at)

    def _success(
        self,
        step: WorkflowStepPlan,
        attempt: int,
        message: str,
        data: dict[str, object],
        started_at,
    ) -> StepExecutionResult:
        return StepExecutionResult(
            step_key=step.key,
            success=True,
            status=STEP_STATUS_COMPLETED,
            message=message,
            attempts=attempt,
            data=data,
            started_at=started_at,
            completed_at=utc_now(),
        )

    def _failure(
        self,
        step: WorkflowStepPlan,
        attempt: int,
        message: str,
        started_at,
        data: dict[str, object] | None = None,
    ) -> StepExecutionResult:
        return StepExecutionResult(
            step_key=step.key,
            success=False,
            status=STEP_STATUS_FAILED,
            message=message,
            attempts=attempt,
            data=data or {},
            error_message=message,
            started_at=started_at,
            completed_at=utc_now(),
        )
