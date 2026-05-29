"""Reflection engine schemas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkflowReflection:
    """Post-execution analysis for a workflow."""

    workflow_id: str
    success: bool
    summary: str
    failed_steps: tuple[str, ...] = field(default_factory=tuple)
    retry_suggestions: tuple[str, ...] = field(default_factory=tuple)
