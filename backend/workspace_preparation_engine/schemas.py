"""Workspace preparation schemas."""

from __future__ import annotations

from dataclasses import dataclass

from backend.workflow_state_manager.schemas import WorkflowPlan


@dataclass(frozen=True)
class WorkspaceDefinition:
    """Predefined workspace workflow."""

    key: str
    name: str
    description: str
    steps: tuple[str, ...]
    workflow_plan: WorkflowPlan
