from backend.activity_snapshot_manager.service import ActivitySnapshotManager
from backend.context_switching_engine.service import ContextSwitchingEngine
from backend.observer_engine.service import ObserverEngine
from backend.operating_context_manager.schemas import (
    OPERATING_MODE_CODING,
    OPERATING_MODE_ML,
)
from backend.operating_context_manager.service import OperatingContextManager
from backend.resume_engine.service import ResumeEngine
from backend.session_recovery_engine.service import SessionRecoveryEngine
from backend.task_engine.service import TaskEngine
from backend.workflow_state_manager.schemas import WorkflowPlan, WorkflowStepPlan
from backend.workflow_state_manager.service import WorkflowStateManager
from backend.workspace_profile_manager.service import WorkspaceProfileManager
from database.init_db import initialize_database
from tests.helpers import make_test_settings


def _services(settings):
    operating_context = OperatingContextManager(settings=settings)
    workspace_profiles = WorkspaceProfileManager(settings=settings)
    tasks = TaskEngine(settings=settings)
    workflows = WorkflowStateManager(settings=settings)
    observer = ObserverEngine(settings=settings)
    snapshots = ActivitySnapshotManager(
        settings=settings,
        operating_context=operating_context,
        workflow_state=workflows,
        task_engine=tasks,
        observer_engine=observer,
    )
    switching = ContextSwitchingEngine(
        settings=settings,
        operating_context=operating_context,
        workspace_profiles=workspace_profiles,
        snapshots=snapshots,
        workflow_state=workflows,
        task_engine=tasks,
    )
    recovery = SessionRecoveryEngine(
        settings=settings,
        operating_context=operating_context,
        snapshots=snapshots,
        workflow_state=workflows,
        task_engine=tasks,
        observer_engine=observer,
    )
    resume = ResumeEngine(
        settings=settings,
        operating_context=operating_context,
        snapshots=snapshots,
        workflow_state=workflows,
        task_engine=tasks,
        observer_engine=observer,
    )
    return operating_context, workspace_profiles, tasks, workflows, observer, snapshots, switching, recovery, resume


def _workflow_plan() -> WorkflowPlan:
    return WorkflowPlan(
        goal="Continue personal OS layer",
        name="Personal OS Layer",
        steps=(
            WorkflowStepPlan(
                key="implement",
                name="Implement layer",
                action_type="noop",
                position=0,
            ),
        ),
    )


def test_workspace_profile_defaults_and_custom_workspace(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    _, profiles, *_ = _services(settings)

    names = {profile.name for profile in profiles.list_profiles()}
    custom = profiles.create_custom_workspace(
        "Paper Reading",
        focus_area="Transformer papers",
        default_goals=("Read one paper",),
    )

    assert {"ML Workspace", "Coding Workspace", "Revision Workspace"} <= names
    assert custom.key == "paper_reading"
    assert custom.focus_area == "Transformer papers"


def test_context_switching_saves_current_context_and_pauses_workflows(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    operating_context, _, _, workflows, _, _, switching, *_ = _services(settings)
    workflow = workflows.create_workflow(_workflow_plan())
    workflows.start_workflow(workflow.id)
    operating_context.update_context(
        operating_mode=OPERATING_MODE_ML,
        current_workspace="ml_workspace",
        focus_area="Model notes",
    )

    result = switching.switch_workspace("coding_workspace")
    paused = workflows.snapshot(workflow.id).workflow
    context = operating_context.current_context()
    saved = switching.list_saved_contexts()

    assert result.success is True
    assert workflow.id in result.paused_workflow_ids
    assert paused.status == "paused"
    assert context.current_workspace == "coding_workspace"
    assert context.operating_mode == OPERATING_MODE_CODING
    assert saved[0].status == "paused"


def test_activity_snapshot_persists_context_across_instances(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    operating_context, _, tasks, _, _, snapshots, *_ = _services(settings)
    tasks.create_task("Finish snapshot persistence")
    operating_context.update_context(
        operating_mode=OPERATING_MODE_CODING,
        current_workspace="coding_workspace",
        focus_area="Snapshot tests",
        active_documents=("backend/activity_snapshot_manager/service.py",),
    )

    created = snapshots.take_snapshot()
    second_manager = ActivitySnapshotManager(
        settings=settings,
        operating_context=operating_context,
    )
    latest = second_manager.latest_snapshot()

    assert latest is not None
    assert latest.id == created.id
    assert latest.context.focus_area == "Snapshot tests"
    assert latest.pending_tasks == ("Finish snapshot persistence",)


def test_resume_engine_answers_resume_questions(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    operating_context, _, tasks, workflows, _, snapshots, _, _, resume = _services(settings)
    tasks.create_task("Run resume engine tests")
    workflow = workflows.create_workflow(_workflow_plan())
    workflows.start_workflow(workflow.id)
    operating_context.update_context(
        operating_mode=OPERATING_MODE_CODING,
        current_workspace="coding_workspace",
        focus_area="Personal OS layer",
    )
    snapshots.take_snapshot()

    summary = resume.generate_summary()
    pending_answer = resume.answer("what is pending?")

    assert "Personal OS Layer" in summary.what_was_i_doing
    assert any("Run resume engine tests" in item for item in summary.what_is_pending)
    assert "Personal OS Layer" in summary.where_did_i_stop
    assert "Run resume engine tests" in pending_answer


def test_session_recovery_restores_workflows_study_workspace_and_tasks(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    operating_context, _, tasks, workflows, observer, snapshots, _, recovery, _ = _services(settings)
    tasks.create_task("Recover pending task")
    workflow = workflows.create_workflow(_workflow_plan())
    workflows.start_workflow(workflow.id)
    observer.start_study_session("NumPy")
    operating_context.update_context(
        operating_mode=OPERATING_MODE_ML,
        current_workspace="ml_workspace",
        focus_area="Study recovery",
    )
    snapshots.take_snapshot()

    plan = recovery.restore_session()

    assert plan.active_workflows[0].id == workflow.id
    assert plan.active_study_session.topic == "NumPy"
    assert plan.workspace_state.current_workspace == "ml_workspace"
    assert plan.pending_tasks[0].title == "Recover pending task"
    assert "pending task" in plan.summary
