"""Serialization helpers for workflow plans."""

from __future__ import annotations

from uuid import uuid4

from backend.workflow_state_manager.schemas import WorkflowPlan, WorkflowStepPlan


def plan_to_dict(plan: WorkflowPlan) -> dict[str, object]:
    """Convert a workflow plan to a JSON-friendly dictionary."""
    return {
        "id": plan.id,
        "goal": plan.goal,
        "name": plan.name,
        "description": plan.description,
        "source": plan.source,
        "metadata": plan.metadata,
        "created_at": plan.created_at.isoformat(),
        "steps": [
            {
                "key": step.key,
                "name": step.name,
                "action_type": step.action_type,
                "action_name": step.action_name,
                "parameters": step.parameters,
                "depends_on": list(step.depends_on),
                "condition_kind": step.condition_kind,
                "condition_data": step.condition_data,
                "retries": step.retries,
                "timeout_seconds": step.timeout_seconds,
                "continue_on_failure": step.continue_on_failure,
                "position": step.position,
                "agent_id": step.agent_id,
            }
            for step in plan.steps
        ],
    }


def plan_from_dict(payload: dict[str, object]) -> WorkflowPlan:
    """Build a workflow plan from a JSON-friendly dictionary."""
    steps = []
    for index, raw_step in enumerate(payload.get("steps", [])):
        if not isinstance(raw_step, dict):
            continue
        steps.append(
            WorkflowStepPlan(
                key=str(raw_step.get("key", f"step_{index + 1}")),
                name=str(raw_step.get("name", f"Step {index + 1}")),
                action_type=str(raw_step.get("action_type", "noop")),
                action_name=str(raw_step.get("action_name", "")),
                parameters=dict(raw_step.get("parameters", {}) or {}),
                depends_on=tuple(raw_step.get("depends_on", []) or []),
                condition_kind=str(raw_step.get("condition_kind", "always")),
                condition_data=dict(raw_step.get("condition_data", {}) or {}),
                retries=int(raw_step.get("retries", 0) or 0),
                timeout_seconds=_optional_float(raw_step.get("timeout_seconds")),
                continue_on_failure=bool(raw_step.get("continue_on_failure", False)),
                position=int(raw_step.get("position", index) or index),
                agent_id=str(raw_step.get("agent_id", "local")),
            )
        )

    return WorkflowPlan(
        id=str(payload.get("id", "")) or str(uuid4()),
        goal=str(payload.get("goal", "")),
        name=str(payload.get("name", "Workflow")),
        description=str(payload.get("description", "")),
        source=str(payload.get("source", "serialized")),
        metadata=dict(payload.get("metadata", {}) or {}),
        steps=tuple(steps),
    )


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
