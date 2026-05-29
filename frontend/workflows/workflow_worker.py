"""Background worker for agentic workflow execution."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from backend.goal_planner_engine.service import GoalPlannerEngine
from backend.workflow_execution_engine.service import WorkflowExecutionEngine
from backend.workflow_state_manager.schemas import WorkflowExecutionResult, WorkflowPlan

logger = logging.getLogger(__name__)


class WorkflowExecutionWorker(QThread):
    """Runs a planned workflow away from the UI thread."""

    started_workflow = pyqtSignal(str, str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        goal_planner: GoalPlannerEngine,
        workflow_execution: WorkflowExecutionEngine,
        goal: str,
        plan: WorkflowPlan | None = None,
    ) -> None:
        super().__init__()
        self.goal_planner = goal_planner
        self.workflow_execution = workflow_execution
        self.goal = goal
        self.plan = plan

    def run(self) -> None:
        """Plan and execute the workflow."""
        try:
            plan = self.plan or self.goal_planner.create_plan(self.goal)
            self.started_workflow.emit(plan.id, plan.name)
            result: WorkflowExecutionResult = self.workflow_execution.execute_plan(plan)
            self.completed.emit(result)
        except Exception as exc:
            logger.exception("Workflow worker failed")
            self.failed.emit(str(exc))
