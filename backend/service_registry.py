"""Composition root for backend engines."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from backend.application_state_manager.service import ApplicationStateManager
from backend.ai_engine.service import AIEngine
from backend.analytics_engine.service import AnalyticsEngine
from backend.activity_snapshot_manager.service import ActivitySnapshotManager
from backend.automation_engine.service import AutomationEngine
from backend.behavioral_pattern_engine.service import BehavioralPatternEngine
from backend.centralized_event_bus.service import CentralizedEventBus
from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_OBSERVER,
    PRIORITY_NORMAL,
    PlatformEvent,
)
from backend.companion_interaction_manager.service import CompanionInteractionManager
from backend.code_intelligence_engine.service import CodeIntelligenceEngine
from backend.content_summarization_engine.service import ContentSummarizationEngine
from backend.contextual_recommendation_engine.service import ContextualRecommendationEngine
from backend.context_understanding_engine.service import ContextUnderstandingEngine
from backend.context_switching_engine.service import ContextSwitchingEngine
from backend.daily_summary_engine.service import DailySummaryEngine
from backend.daily_reflection_engine.service import DailyReflectionEngine
from backend.daily_timeline_manager.service import DailyTimelineManager
from backend.document_intelligence_engine.service import DocumentIntelligenceEngine
from backend.error_recovery_engine.service import ErrorRecoveryEngine
from backend.execution_sandbox.schemas import ExecutionQuota
from backend.execution_sandbox.service import ExecutionSandbox
from backend.goal_planner_engine.service import GoalPlannerEngine
from backend.focus_scoring_engine.service import FocusScoringEngine
from backend.knowledge_memory_manager.service import KnowledgeMemoryManager
from backend.lifecycle_manager.service import LifecycleManager
from backend.memory_engine.service import MemoryEngine
from backend.notification_decision_engine.service import NotificationDecisionEngine
from backend.notification_engine.service import NotificationEngine
from backend.observability_engine.service import ObservabilityEngine
from backend.observer_engine.service import ObserverEngine
from backend.observer_engine.observer_event_bus.events import SUPPORTED_OBSERVER_EVENTS
from backend.operating_context_manager.service import OperatingContextManager
from backend.performance_monitor.schemas import PerformanceThresholds
from backend.performance_monitor.service import PerformanceMonitor
from backend.planner_engine.service import PlannerEngine
from backend.productivity_analyzer.service import ProductivityAnalyzer
from backend.recommendation_engine.repository import RecommendationLogRepository
from backend.recommendation_engine.service import RecommendationEngine
from backend.reflection_engine.service import ReflectionEngine
from backend.resume_engine.service import ResumeEngine
from backend.screen_intelligence_engine.service import ScreenIntelligenceEngine
from backend.session_recovery_engine.service import SessionRecoveryEngine
from backend.task_engine.service import TaskEngine
from backend.workflow_execution_engine.service import WorkflowExecutionEngine
from backend.workflow_memory_manager.service import WorkflowMemoryManager
from backend.workflow_scheduler.service import WorkflowScheduler
from backend.workflow_state_manager.event_bus import WorkflowEventBus
from backend.workflow_state_manager.service import WorkflowStateManager
from backend.workflow_validator.service import WorkflowValidator
from backend.structured_config_system.service import StructuredConfigSystem
from backend.startup_briefing_engine.service import StartupBriefingEngine
from backend.workspace_preparation_engine.service import WorkspacePreparationEngine
from backend.workspace_profile_manager.service import WorkspaceProfileManager


@dataclass
class ServiceRegistry:
    """Container for long-lived backend services."""

    ai: AIEngine
    planner: PlannerEngine
    automation: AutomationEngine
    observer: ObserverEngine
    analytics: AnalyticsEngine
    memory: MemoryEngine
    notifications: NotificationEngine
    notification_decisions: NotificationDecisionEngine
    focus_scoring: FocusScoringEngine
    productivity_analyzer: ProductivityAnalyzer
    behavioral_patterns: BehavioralPatternEngine
    recommendations: RecommendationEngine
    daily_summaries: DailySummaryEngine
    tasks: TaskEngine
    goal_planner: GoalPlannerEngine
    workflow_state: WorkflowStateManager
    workflow_validator: WorkflowValidator
    workflow_memory: WorkflowMemoryManager
    reflection: ReflectionEngine
    workflow_execution: WorkflowExecutionEngine
    workflow_scheduler: WorkflowScheduler
    event_bus: CentralizedEventBus
    app_state: ApplicationStateManager
    structured_config: StructuredConfigSystem
    observability: ObservabilityEngine
    execution_sandbox: ExecutionSandbox
    performance_monitor: PerformanceMonitor
    lifecycle: LifecycleManager
    error_recovery: ErrorRecoveryEngine
    startup_briefings: StartupBriefingEngine
    daily_reflections: DailyReflectionEngine
    contextual_recommendations: ContextualRecommendationEngine
    workspace_preparation: WorkspacePreparationEngine
    companion_interactions: CompanionInteractionManager
    daily_timeline: DailyTimelineManager
    content_summarization: ContentSummarizationEngine
    context_understanding: ContextUnderstandingEngine
    document_intelligence: DocumentIntelligenceEngine
    code_intelligence: CodeIntelligenceEngine
    screen_intelligence: ScreenIntelligenceEngine
    knowledge_memory: KnowledgeMemoryManager
    operating_context: OperatingContextManager
    workspace_profiles: WorkspaceProfileManager
    activity_snapshots: ActivitySnapshotManager
    context_switching: ContextSwitchingEngine
    session_recovery: SessionRecoveryEngine
    resume_engine: ResumeEngine


def build_services(settings: AppSettings) -> ServiceRegistry:
    """Instantiate backend engines with shared settings."""
    event_bus = CentralizedEventBus()
    app_state = ApplicationStateManager()
    observability = ObservabilityEngine(state_manager=app_state)
    structured_config = StructuredConfigSystem(settings=settings)
    structured_config.load()
    performance_monitor = PerformanceMonitor(
        thresholds=PerformanceThresholds(
            memory_warning_mb=settings.performance_memory_warning_mb,
            event_rate_warning_per_minute=settings.performance_event_rate_warning_per_minute,
        )
    )
    execution_sandbox = ExecutionSandbox(
        safe_mode=settings.sandbox_safe_mode_default,
        emergency_stop=settings.sandbox_emergency_stop_default,
        default_quota=ExecutionQuota(
            max_calls=settings.sandbox_rate_limit_max_calls,
            window_seconds=settings.sandbox_rate_limit_window_seconds,
        ),
    )
    lifecycle = LifecycleManager(event_bus=event_bus)
    error_recovery = ErrorRecoveryEngine(event_bus=event_bus)
    event_bus.subscribe(app_state.handle_event, name="application_state_manager")
    event_bus.subscribe(observability.handle_event, name="observability_engine")

    memory = MemoryEngine(settings=settings, event_bus=event_bus)
    operating_context = OperatingContextManager(
        settings=settings,
        memory_engine=memory,
    )
    workspace_profiles = WorkspaceProfileManager(settings=settings)
    content_summarization = ContentSummarizationEngine()
    context_understanding = ContextUnderstandingEngine()
    document_intelligence = DocumentIntelligenceEngine(
        settings=settings,
        summarizer=content_summarization,
        context_engine=context_understanding,
    )
    code_intelligence = CodeIntelligenceEngine(
        settings=settings,
        context_engine=context_understanding,
    )
    screen_intelligence = ScreenIntelligenceEngine(
        settings=settings,
        summarizer=content_summarization,
        context_engine=context_understanding,
    )
    knowledge_memory = KnowledgeMemoryManager(
        settings=settings,
        memory_engine=memory,
        event_bus=event_bus,
    )
    analytics = AnalyticsEngine(settings=settings)
    tasks = TaskEngine(settings=settings, analytics_engine=analytics)
    automation = AutomationEngine(
        settings=settings,
        event_bus=event_bus,
        execution_sandbox=execution_sandbox,
    )
    workflow_event_bus = WorkflowEventBus()
    workflow_state = WorkflowStateManager(
        settings=settings,
        event_bus=workflow_event_bus,
        platform_event_bus=event_bus,
    )
    focus_scoring = FocusScoringEngine(settings=settings)
    productivity_analyzer = ProductivityAnalyzer(
        settings=settings,
        focus_scoring_engine=focus_scoring,
    )
    behavioral_patterns = BehavioralPatternEngine(settings=settings)
    recommendation_logs = RecommendationLogRepository.from_settings(settings)
    ai = AIEngine(
        settings=settings,
        task_engine=tasks,
        automation_engine=automation,
        memory_engine=memory,
        event_bus=event_bus,
        observability=observability,
        error_recovery=error_recovery,
    )
    recommendations = RecommendationEngine(
        settings=settings,
        repository=recommendation_logs,
        ollama_service=ai.ollama_service,
        prompt_manager=ai.prompt_manager,
    )
    daily_summaries = DailySummaryEngine(
        settings=settings,
        productivity_analyzer=productivity_analyzer,
        ollama_service=ai.ollama_service,
        prompt_manager=ai.prompt_manager,
    )
    goal_planner = GoalPlannerEngine(
        settings=settings,
        ollama_service=ai.ollama_service,
    )
    workflow_validator = WorkflowValidator(
        settings=settings,
        automation_engine=automation,
    )
    workflow_memory = WorkflowMemoryManager(settings=settings)
    reflection = ReflectionEngine(
        settings=settings,
        workflow_memory=workflow_memory,
        ollama_service=ai.ollama_service,
    )
    observer = ObserverEngine(settings=settings)
    for observer_event_type in SUPPORTED_OBSERVER_EVENTS:
        observer.subscribe(
            observer_event_type,
            lambda event, event_bus=event_bus: event_bus.publish(
                PlatformEvent(
                    event_type=event.event_type,
                    source="observer_engine",
                    category=EVENT_CATEGORY_OBSERVER,
                    priority=PRIORITY_NORMAL,
                    payload=event.payload,
                    created_at=event.created_at,
                )
            ),
        )
    notifications = NotificationEngine(settings=settings, event_bus=event_bus)
    workflow_execution = WorkflowExecutionEngine(
        settings=settings,
        state_manager=workflow_state,
        validator=workflow_validator,
        automation_engine=automation,
        observer_engine=observer,
        notification_engine=notifications,
        reflection_engine=reflection,
        execution_sandbox=execution_sandbox,
        performance_monitor=performance_monitor,
    )
    workflow_scheduler = WorkflowScheduler(
        settings=settings,
        goal_planner=goal_planner,
    )
    activity_snapshots = ActivitySnapshotManager(
        settings=settings,
        operating_context=operating_context,
        workflow_state=workflow_state,
        task_engine=tasks,
        observer_engine=observer,
    )
    context_switching = ContextSwitchingEngine(
        settings=settings,
        operating_context=operating_context,
        workspace_profiles=workspace_profiles,
        snapshots=activity_snapshots,
        workflow_state=workflow_state,
        workflow_execution=workflow_execution,
        task_engine=tasks,
    )
    session_recovery = SessionRecoveryEngine(
        settings=settings,
        operating_context=operating_context,
        snapshots=activity_snapshots,
        workflow_state=workflow_state,
        workflow_execution=workflow_execution,
        task_engine=tasks,
        observer_engine=observer,
    )
    resume_engine = ResumeEngine(
        settings=settings,
        operating_context=operating_context,
        snapshots=activity_snapshots,
        workflow_state=workflow_state,
        task_engine=tasks,
        observer_engine=observer,
    )
    daily_timeline = DailyTimelineManager(settings=settings)
    companion_interactions = CompanionInteractionManager(settings=settings)
    startup_briefings = StartupBriefingEngine(
        settings=settings,
        task_engine=tasks,
        daily_summary_engine=daily_summaries,
        productivity_analyzer=productivity_analyzer,
        workflow_state=workflow_state,
    )
    daily_reflections = DailyReflectionEngine(
        settings=settings,
        productivity_analyzer=productivity_analyzer,
        recommendation_repository=recommendation_logs,
    )
    contextual_recommendations = ContextualRecommendationEngine(
        settings=settings,
        task_engine=tasks,
        productivity_analyzer=productivity_analyzer,
        workflow_memory=workflow_memory,
        workflow_state=workflow_state,
    )
    workspace_preparation = WorkspacePreparationEngine(settings=settings)
    ai.action_router.goal_planner = goal_planner
    ai.action_router.workflow_execution_engine = workflow_execution
    ai.action_router.resume_engine = resume_engine
    lifecycle.register("event_bus")
    lifecycle.register("application_state", dependencies=("event_bus",))
    lifecycle.register("observability", dependencies=("application_state",))
    lifecycle.register("sandbox", dependencies=("event_bus",))
    lifecycle.register("backend_services", dependencies=("observability", "sandbox"))
    lifecycle.start_all()

    return ServiceRegistry(
        ai=ai,
        planner=PlannerEngine(settings=settings, ai_engine=ai, memory_engine=memory),
        automation=automation,
        observer=observer,
        analytics=analytics,
        memory=memory,
        notifications=notifications,
        notification_decisions=NotificationDecisionEngine(
            settings=settings,
            repository=recommendation_logs,
        ),
        focus_scoring=focus_scoring,
        productivity_analyzer=productivity_analyzer,
        behavioral_patterns=behavioral_patterns,
        recommendations=recommendations,
        daily_summaries=daily_summaries,
        tasks=tasks,
        goal_planner=goal_planner,
        workflow_state=workflow_state,
        workflow_validator=workflow_validator,
        workflow_memory=workflow_memory,
        reflection=reflection,
        workflow_execution=workflow_execution,
        workflow_scheduler=workflow_scheduler,
        event_bus=event_bus,
        app_state=app_state,
        structured_config=structured_config,
        observability=observability,
        execution_sandbox=execution_sandbox,
        performance_monitor=performance_monitor,
        lifecycle=lifecycle,
        error_recovery=error_recovery,
        startup_briefings=startup_briefings,
        daily_reflections=daily_reflections,
        contextual_recommendations=contextual_recommendations,
        workspace_preparation=workspace_preparation,
        companion_interactions=companion_interactions,
        daily_timeline=daily_timeline,
        content_summarization=content_summarization,
        context_understanding=context_understanding,
        document_intelligence=document_intelligence,
        code_intelligence=code_intelligence,
        screen_intelligence=screen_intelligence,
        knowledge_memory=knowledge_memory,
        operating_context=operating_context,
        workspace_profiles=workspace_profiles,
        activity_snapshots=activity_snapshots,
        context_switching=context_switching,
        session_recovery=session_recovery,
        resume_engine=resume_engine,
    )
