from datetime import timedelta

from backend.automation_engine.app_launcher.service import AppLauncher
from backend.automation_engine.browser_automation.service import BrowserAutomation
from backend.automation_engine.service import AutomationEngine
from backend.goal_planner_engine.service import GoalPlannerEngine
from backend.reflection_engine.service import ReflectionEngine
from backend.workflow_execution_engine.service import WorkflowExecutionEngine
from backend.workflow_memory_manager.service import WorkflowMemoryManager
from backend.workflow_scheduler.service import WorkflowScheduler
from backend.workflow_state_manager.schemas import (
    ACTION_TYPE_AUTOMATION,
    ACTION_TYPE_NOOP,
    STEP_STATUS_COMPLETED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WorkflowPlan,
    WorkflowStepPlan,
)
from backend.workflow_state_manager.service import WorkflowStateManager
from backend.workflow_validator.service import WorkflowValidator
from database.init_db import initialize_database
from database.models import utc_now
from tests.helpers import make_test_settings


def _fake_automation(settings):
    launched = []
    opened_urls = []
    return (
        AutomationEngine(
            settings=settings,
            app_launcher=AppLauncher(settings, runner=launched.append),
            browser=BrowserAutomation(opener=lambda url: opened_urls.append(url) or True),
        ),
        launched,
        opened_urls,
    )


def _workflow_services(settings, automation):
    state = WorkflowStateManager(settings=settings)
    validator = WorkflowValidator(settings=settings, automation_engine=automation)
    memory = WorkflowMemoryManager(settings=settings)
    reflection = ReflectionEngine(settings=settings, workflow_memory=memory)
    executor = WorkflowExecutionEngine(
        settings=settings,
        state_manager=state,
        validator=validator,
        automation_engine=automation,
        reflection_engine=reflection,
    )
    return state, validator, memory, reflection, executor


def test_goal_planner_creates_study_workflow_with_dependencies(tmp_path):
    settings = make_test_settings(tmp_path)
    planner = GoalPlannerEngine(settings=settings)

    plan = planner.create_plan("Prepare ML study session")

    assert plan.name == "ML Study Session"
    assert [step.name for step in plan.steps] == [
        "Open VS Code",
        "Open notebook",
        "Start Study Mode",
        "Open reference material",
        "Start focus timer",
    ]
    assert plan.steps[1].depends_on == ("open_vscode",)


def test_workflow_validator_blocks_dangerous_parameters(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, *_ = _fake_automation(settings)
    validator = WorkflowValidator(settings=settings, automation_engine=automation)
    plan = WorkflowPlan(
        goal="unsafe",
        name="Unsafe Workflow",
        steps=(
            WorkflowStepPlan(
                key="unsafe",
                name="Unsafe",
                action_type=ACTION_TYPE_AUTOMATION,
                parameters={
                    "tool_name": "open_app",
                    "parameters": {"app_name": "shutdown system"},
                },
            ),
        ),
    )

    result = validator.validate(plan)

    assert result.is_valid is False
    assert "unsafe parameters" in result.message


def test_workflow_execution_persists_success_and_memory(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, launched, _ = _fake_automation(settings)
    state, _, memory, _, executor = _workflow_services(settings, automation)
    plan = WorkflowPlan(
        goal="Open editor",
        name="Editor Workflow",
        steps=(
            WorkflowStepPlan(
                key="open_editor",
                name="Open editor",
                action_type=ACTION_TYPE_AUTOMATION,
                parameters={
                    "tool_name": "open_app",
                    "parameters": {"app_name": "vscode"},
                },
            ),
            WorkflowStepPlan(
                key="done",
                name="Mark ready",
                action_type=ACTION_TYPE_NOOP,
                depends_on=("open_editor",),
                parameters={"message": "Editor ready"},
                position=1,
            ),
        ),
    )

    result = executor.execute_plan(plan)
    snapshot = state.snapshot(result.workflow_id)
    patterns = memory.list_patterns()

    assert result.success is True
    assert snapshot.workflow.status == WORKFLOW_STATUS_COMPLETED
    assert snapshot.steps[0].status == STEP_STATUS_COMPLETED
    assert launched == [["code"]]
    assert patterns[0]["outcome"] == "success"


def test_workflow_execution_retries_and_fails_safely(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, _, _ = _fake_automation(settings)
    state, _, _, _, executor = _workflow_services(settings, automation)
    plan = WorkflowPlan(
        goal="Open unknown editor",
        name="Failing Workflow",
        steps=(
            WorkflowStepPlan(
                key="open_missing",
                name="Open missing app",
                action_type=ACTION_TYPE_AUTOMATION,
                parameters={
                    "tool_name": "open_app",
                    "parameters": {"app_name": "missing-app"},
                },
                retries=1,
            ),
        ),
    )

    result = executor.execute_plan(plan)
    snapshot = state.snapshot(result.workflow_id)

    assert result.success is False
    assert result.status == WORKFLOW_STATUS_FAILED
    assert result.step_results[0].attempts == 2
    assert snapshot.workflow.status == WORKFLOW_STATUS_FAILED


def test_reflection_detects_failed_steps_and_suggestions(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, _, _ = _fake_automation(settings)
    _, _, _, reflection, executor = _workflow_services(settings, automation)
    plan = WorkflowPlan(
        goal="Open unknown editor",
        name="Failing Workflow",
        steps=(
            WorkflowStepPlan(
                key="open_missing",
                name="Open missing app",
                action_type=ACTION_TYPE_AUTOMATION,
                parameters={
                    "tool_name": "open_app",
                    "parameters": {"app_name": "missing-app"},
                },
            ),
        ),
    )

    result = executor.execute_plan(plan)
    analysis = reflection.reflect(plan, result)

    assert analysis.success is False
    assert analysis.failed_steps == ("open_missing",)
    assert "Retry" in analysis.retry_suggestions[0]


def test_workflow_scheduler_returns_due_study_session(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    planner = GoalPlannerEngine(settings=settings)
    scheduler = WorkflowScheduler(settings=settings, goal_planner=planner)
    run_at = utc_now() - timedelta(seconds=1)

    schedule_id = scheduler.schedule_study_session("NumPy", run_at)
    due = scheduler.due_workflows()
    scheduler.mark_dispatched(schedule_id)

    assert due[0].id == schedule_id
    assert due[0].trigger_type == "study_session"
    assert scheduler.due_workflows() == []
