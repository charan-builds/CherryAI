"""Planner engine.

This engine will turn user goals into ordered steps. Keeping planning separate
from execution lets Cherry AI support reviewable plans, approvals, and retries.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from backend.ai_engine.service import AIEngine
from backend.memory_engine.service import MemoryEngine


@dataclass
class PlannerEngine:
    """Creates structured plans for tasks."""

    settings: AppSettings
    ai_engine: AIEngine
    memory_engine: MemoryEngine

    def create_plan(self, goal: str) -> list[str]:
        """Return a simple placeholder plan for a goal."""
        return [f"Understand goal: {goal}", "Prepare execution steps", "Await approval"]
