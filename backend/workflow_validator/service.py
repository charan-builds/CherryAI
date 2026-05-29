"""Workflow safety and integrity validator."""

from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import AppSettings
from backend.automation_engine.permission_manager.service import BLOCKED_KEYWORDS
from backend.automation_engine.service import AutomationEngine
from backend.workflow_state_manager.schemas import (
    ACTION_TYPE_AUTOMATION,
    ACTION_TYPE_NOOP,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_STUDY_SESSION,
    CONDITION_ALWAYS,
    CONDITION_CONTEXT_EQUALS,
    CONDITION_PREVIOUS_FAILURE,
    CONDITION_PREVIOUS_SUCCESS,
    WorkflowPlan,
    WorkflowStepPlan,
)
from backend.workflow_validator.schemas import WorkflowValidationResult

ALLOWED_ACTION_TYPES = {
    ACTION_TYPE_AUTOMATION,
    ACTION_TYPE_STUDY_SESSION,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_NOOP,
}
ALLOWED_CONDITIONS = {
    CONDITION_ALWAYS,
    CONDITION_PREVIOUS_SUCCESS,
    CONDITION_PREVIOUS_FAILURE,
    CONDITION_CONTEXT_EQUALS,
}


@dataclass
class WorkflowValidator:
    """Validates workflow integrity before execution."""

    settings: AppSettings
    automation_engine: AutomationEngine | None = None
    allowed_tools: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.allowed_tools and self.automation_engine is not None:
            self.allowed_tools = {tool.name for tool in self.automation_engine.list_tools()}

    def validate(self, plan: WorkflowPlan) -> WorkflowValidationResult:
        """Validate a complete workflow plan."""
        errors: list[str] = []
        warnings: list[str] = []

        if not plan.goal.strip():
            errors.append("Workflow goal is required.")
        if not plan.steps:
            errors.append("Workflow must contain at least one step.")
        if len(plan.steps) > self.settings.workflow_max_steps:
            errors.append(
                f"Workflow has too many steps. Maximum is {self.settings.workflow_max_steps}."
            )

        step_keys = [step.key for step in plan.steps]
        if len(step_keys) != len(set(step_keys)):
            errors.append("Workflow step keys must be unique.")

        step_lookup = {step.key: step for step in plan.steps}
        for step in plan.steps:
            self._validate_step(step, step_lookup, errors, warnings)

        if self._has_dependency_cycle(step_lookup):
            errors.append("Workflow dependencies contain a cycle.")

        return WorkflowValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def _validate_step(
        self,
        step: WorkflowStepPlan,
        step_lookup: dict[str, WorkflowStepPlan],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        if not step.key.strip():
            errors.append("Workflow step key is required.")
        if not step.name.strip():
            errors.append(f"Step '{step.key}' must have a readable name.")
        if step.action_type not in ALLOWED_ACTION_TYPES:
            errors.append(f"Step '{step.key}' uses unsupported action type.")
        if step.condition_kind not in ALLOWED_CONDITIONS:
            errors.append(f"Step '{step.key}' uses unsupported condition.")

        for dependency in step.depends_on:
            if dependency not in step_lookup:
                errors.append(
                    f"Step '{step.key}' depends on unknown step '{dependency}'."
                )

        if step.retries < 0 or step.retries > self.settings.workflow_max_retries:
            errors.append(
                f"Step '{step.key}' retries must be between 0 and "
                f"{self.settings.workflow_max_retries}."
            )

        if step.timeout_seconds is not None and step.timeout_seconds <= 0:
            errors.append(f"Step '{step.key}' timeout must be positive.")

        if self._contains_blocked_keyword(step.parameters):
            errors.append(f"Step '{step.key}' contains unsafe parameters.")

        if step.action_type == ACTION_TYPE_AUTOMATION:
            self._validate_automation_step(step, errors, warnings)
        elif step.action_type == ACTION_TYPE_STUDY_SESSION:
            if step.action_name not in {"start", "stop"}:
                errors.append(
                    f"Step '{step.key}' study action must be 'start' or 'stop'."
                )
        elif step.action_type == ACTION_TYPE_NOTIFICATION:
            if not str(step.parameters.get("message", "")).strip():
                errors.append(f"Step '{step.key}' notification message is required.")

    def _validate_automation_step(
        self,
        step: WorkflowStepPlan,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        tool_name = str(step.parameters.get("tool_name", "")).strip()
        if not tool_name:
            errors.append(f"Step '{step.key}' automation tool_name is required.")
            return
        if self.allowed_tools and tool_name not in self.allowed_tools:
            errors.append(f"Step '{step.key}' uses blocked or unknown tool '{tool_name}'.")
        if tool_name == "take_screenshot":
            warnings.append(
                f"Step '{step.key}' may require confirmation before execution."
            )

    def _contains_blocked_keyword(self, payload: object) -> bool:
        haystack = self._flatten_payload(payload).lower()
        return any(keyword in haystack for keyword in BLOCKED_KEYWORDS)

    def _flatten_payload(self, payload: object) -> str:
        if isinstance(payload, dict):
            return " ".join(self._flatten_payload(value) for value in payload.values())
        if isinstance(payload, (list, tuple, set)):
            return " ".join(self._flatten_payload(value) for value in payload)
        return str(payload)

    def _has_dependency_cycle(
        self,
        step_lookup: dict[str, WorkflowStepPlan],
    ) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_key: str) -> bool:
            if step_key in visited:
                return False
            if step_key in visiting:
                return True
            visiting.add(step_key)
            step = step_lookup.get(step_key)
            if step is None:
                visiting.remove(step_key)
                return False
            for dependency in step.depends_on:
                if visit(dependency):
                    return True
            visiting.remove(step_key)
            visited.add(step_key)
            return False

        return any(visit(step_key) for step_key in step_lookup)
