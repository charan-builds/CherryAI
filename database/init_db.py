"""Database initialization."""

from __future__ import annotations

import logging

from config.settings import AppSettings
from database.ai_models import AIInteraction  # noqa: F401
from database.automation_models import (  # noqa: F401
    AutomationActionLog,
    PermissionDecisionLog,
    ToolExecutionLog,
)
from database.base import Base
from database.companion_models import CompanionInteractionLog, DailyTimelineEntry  # noqa: F401
from database.memory_models import (  # noqa: F401
    ConsolidatedMemoryPattern,
    SemanticMemory,
    WorkingMemoryState,
)
from database.knowledge_models import KnowledgeMemory  # noqa: F401
from database.models import AppMetadata
from database.observer_models import ActivityLog, ObserverEventLog, StudySession  # noqa: F401
from database.operating_context_models import (  # noqa: F401
    ActivitySnapshot,
    OperatingContextState,
    SavedOperatingContext,
    WorkspaceProfile,
)
from database.proactive_models import (  # noqa: F401
    BehavioralPattern,
    ProductivitySummary,
    RecommendationLog,
)
from database.session import create_database_engine, create_session_factory
from database.task_models import Task  # noqa: F401 - imported so metadata is registered
from database.workflow_models import (  # noqa: F401
    ScheduledWorkflow,
    Workflow,
    WorkflowExecutionLog,
    WorkflowHistory,
    WorkflowMemory,
    WorkflowStep,
)

logger = logging.getLogger(__name__)


def initialize_database(settings: AppSettings) -> None:
    """Create local SQLite storage and seed baseline metadata."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    engine = create_database_engine(settings)
    Base.metadata.create_all(bind=engine)

    session_factory = create_session_factory(engine)
    with session_factory() as session:
        schema_version = session.get(AppMetadata, "schema_version")
        if schema_version is None:
            session.add(AppMetadata(key="schema_version", value="1"))
            session.commit()
            logger.info("Seeded database schema metadata")
        else:
            logger.debug("Database schema metadata already present")
