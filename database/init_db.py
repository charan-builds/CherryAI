"""Database initialization."""

from __future__ import annotations

import logging

from config.settings import AppSettings
from database.ai_models import AIInteraction  # noqa: F401
from database.base import Base
from database.models import AppMetadata
from database.observer_models import ActivityLog, ObserverEventLog, StudySession  # noqa: F401
from database.session import create_database_engine, create_session_factory
from database.task_models import Task  # noqa: F401 - imported so metadata is registered

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
