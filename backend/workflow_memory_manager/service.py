"""Workflow memory manager."""

from __future__ import annotations

import re
from dataclasses import dataclass

from config.settings import AppSettings
from backend.workflow_state_manager.repository import WorkflowRepository
from backend.workflow_state_manager.schemas import WorkflowExecutionResult, WorkflowPlan
from backend.workflow_state_manager.serialization import plan_to_dict


@dataclass
class WorkflowMemoryManager:
    """Persists workflow outcomes and reusable execution patterns."""

    settings: AppSettings
    repository: WorkflowRepository | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or WorkflowRepository.from_settings(
            self.settings
        )

    def remember_execution(
        self,
        plan: WorkflowPlan,
        result: WorkflowExecutionResult,
        summary: str,
    ) -> None:
        """Store a successful or failed workflow pattern."""
        outcome = "success" if result.success else "failure"
        self.repository.upsert_memory(
            goal_signature=self.goal_signature(plan.goal),
            workflow_name=plan.name,
            outcome=outcome,
            plan_json=plan_to_dict(plan),
            summary=summary,
            preferred=result.success,
        )

    def list_patterns(self, limit: int = 20) -> list[dict[str, object]]:
        """Return recent workflow memory patterns."""
        return self.repository.list_memory(limit=limit)

    def preferred_for_goal(self, goal: str) -> dict[str, object] | None:
        """Return a preferred workflow memory for a similar goal."""
        signature = self.goal_signature(goal)
        for memory in self.repository.list_memory(limit=50):
            if memory["goal_signature"] == signature and memory["preferred"]:
                return memory
        return None

    def goal_signature(self, goal: str) -> str:
        """Normalize a goal into a compact matching signature."""
        normalized = re.sub(r"[^a-z0-9 ]+", " ", goal.lower())
        words = [word for word in normalized.split() if len(word) > 2]
        return " ".join(words[:8]) or "general"
