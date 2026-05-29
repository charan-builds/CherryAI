"""Workspace preparation engine."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from backend.workflow_state_manager.schemas import (
    ACTION_TYPE_AUTOMATION,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_STUDY_SESSION,
    WorkflowPlan,
    WorkflowStepPlan,
)
from backend.workspace_preparation_engine.schemas import WorkspaceDefinition


@dataclass
class WorkspacePreparationEngine:
    """Creates predefined productivity workspace workflows."""

    settings: AppSettings

    def list_workspaces(self) -> list[WorkspaceDefinition]:
        """Return all predefined workspace definitions."""
        return [
            self.get_workspace("ml_study"),
            self.get_workspace("revision"),
            self.get_workspace("coding"),
        ]

    def get_workspace(self, key: str) -> WorkspaceDefinition:
        """Return a predefined workspace by key."""
        normalized = key.strip().lower()
        if normalized == "revision":
            return self._revision_workspace()
        if normalized == "coding":
            return self._coding_workspace()
        return self._ml_workspace()

    def _ml_workspace(self) -> WorkspaceDefinition:
        plan = WorkflowPlan(
            goal="Prepare ML study workspace",
            name="ML Study Workspace",
            description="Open the core ML study tools and start Study Mode.",
            source="workspace_preparation",
            metadata={"workspace_key": "ml_study"},
            steps=(
                self._open_app("open_vscode", "Open VS Code", "vscode", 0),
                self._open_website(
                    "open_dataset",
                    "Open Dataset Folder",
                    "https://www.kaggle.com/datasets",
                    ("open_vscode",),
                    1,
                ),
                self._open_website(
                    "open_notes",
                    "Open Notes",
                    "https://docs.google.com/",
                    ("open_vscode",),
                    2,
                ),
                WorkflowStepPlan(
                    key="enable_study_mode",
                    name="Enable Study Mode",
                    action_type=ACTION_TYPE_STUDY_SESSION,
                    action_name="start",
                    parameters={"topic": "ML Study"},
                    depends_on=("open_vscode",),
                    position=3,
                ),
            ),
        )
        return self._definition("ml_study", plan)

    def _revision_workspace(self) -> WorkspaceDefinition:
        plan = WorkflowPlan(
            goal="Prepare revision workspace",
            name="Revision Workspace",
            description="Open notes, reference material, and a focus reminder.",
            source="workspace_preparation",
            metadata={"workspace_key": "revision"},
            steps=(
                self._open_website(
                    "open_revision_notes",
                    "Open revision notes",
                    "https://docs.google.com/",
                    (),
                    0,
                ),
                self._open_website(
                    "open_reference",
                    "Open reference material",
                    "https://www.google.com/search?q=revision+practice",
                    ("open_revision_notes",),
                    1,
                ),
                self._notify("revision_timer", "Start revision timer", "Revision block started.", 2),
            ),
        )
        return self._definition("revision", plan)

    def _coding_workspace(self) -> WorkspaceDefinition:
        plan = WorkflowPlan(
            goal="Prepare coding workspace",
            name="Coding Workspace",
            description="Open editor, docs, and coding focus context.",
            source="workspace_preparation",
            metadata={"workspace_key": "coding"},
            steps=(
                self._open_app("open_vscode", "Open VS Code", "vscode", 0),
                self._open_website(
                    "open_docs",
                    "Open docs",
                    "https://docs.python.org/3/",
                    ("open_vscode",),
                    1,
                ),
                self._notify("coding_ready", "Set coding intention", "Coding workspace ready.", 2),
            ),
        )
        return self._definition("coding", plan)

    def _open_app(
        self,
        key: str,
        name: str,
        app_name: str,
        position: int,
    ) -> WorkflowStepPlan:
        return WorkflowStepPlan(
            key=key,
            name=name,
            action_type=ACTION_TYPE_AUTOMATION,
            action_name="open_app",
            parameters={
                "tool_name": "open_app",
                "parameters": {"app_name": app_name},
            },
            retries=self.settings.workflow_default_retries,
            position=position,
        )

    def _open_website(
        self,
        key: str,
        name: str,
        url: str,
        depends_on: tuple[str, ...],
        position: int,
    ) -> WorkflowStepPlan:
        return WorkflowStepPlan(
            key=key,
            name=name,
            action_type=ACTION_TYPE_AUTOMATION,
            action_name="open_website",
            parameters={
                "tool_name": "open_website",
                "parameters": {"url": url},
            },
            depends_on=depends_on,
            retries=self.settings.workflow_default_retries,
            position=position,
        )

    def _notify(
        self,
        key: str,
        name: str,
        message: str,
        position: int,
    ) -> WorkflowStepPlan:
        return WorkflowStepPlan(
            key=key,
            name=name,
            action_type=ACTION_TYPE_NOTIFICATION,
            action_name="notify",
            parameters={"message": message},
            position=position,
        )

    def _definition(self, key: str, plan: WorkflowPlan) -> WorkspaceDefinition:
        return WorkspaceDefinition(
            key=key,
            name=plan.name,
            description=plan.description,
            steps=tuple(step.name for step in plan.steps),
            workflow_plan=plan,
        )
