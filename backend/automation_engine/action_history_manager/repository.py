"""Repository for automation action history."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.automation_models import (
    AutomationActionLog,
    PermissionDecisionLog,
    ToolExecutionLog,
)
from database.session import create_database_engine, create_session_factory
from backend.automation_engine.schemas import AutomationActionRecord


class ActionHistoryRepository:
    """Database access for automation action history."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "ActionHistoryRepository":
        engine = create_database_engine(settings)
        return cls(create_session_factory(engine))

    @contextmanager
    def _session_scope(self) -> Iterator[Session]:
        with self.session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def start_action(
        self,
        tool_name: str,
        parameters: dict[str, object],
        safety_level: str,
        permission_status: str,
        started_at: datetime,
    ) -> str:
        """Create a pending action record and return its id."""
        with self._session_scope() as session:
            log = AutomationActionLog(
                tool_name=tool_name,
                parameters_json=json.dumps(parameters, default=str),
                safety_level=safety_level,
                permission_status=permission_status,
                started_at=started_at,
            )
            session.add(log)
            session.flush()
            return log.id

    def complete_action(
        self,
        action_id: str,
        success: bool,
        message: str,
        error_message: str,
        completed_at: datetime,
    ) -> None:
        """Complete an action record."""
        with self._session_scope() as session:
            log = session.get(AutomationActionLog, action_id)
            if log is None:
                return
            log.success = success
            log.message = message
            log.error_message = error_message
            log.completed_at = completed_at
            log.duration_seconds = self._duration_seconds(log.started_at, completed_at)

    def record_tool_execution(
        self,
        action_id: str,
        tool_name: str,
        result: dict[str, object],
        created_at: datetime,
    ) -> None:
        """Persist lower-level tool execution details."""
        with self._session_scope() as session:
            session.add(
                ToolExecutionLog(
                    action_id=action_id,
                    tool_name=tool_name,
                    result_json=json.dumps(result, default=str),
                    created_at=created_at,
                )
            )

    def record_permission_decision(
        self,
        tool_name: str,
        safety_level: str,
        decision: str,
        reason: str,
        created_at: datetime,
    ) -> None:
        """Persist a permission decision."""
        with self._session_scope() as session:
            session.add(
                PermissionDecisionLog(
                    tool_name=tool_name,
                    safety_level=safety_level,
                    decision=decision,
                    reason=reason,
                    created_at=created_at,
                )
            )

    def list_recent(self, limit: int = 20) -> list[AutomationActionRecord]:
        """Return recent actions newest-first."""
        statement = (
            select(AutomationActionLog)
            .order_by(AutomationActionLog.started_at.desc())
            .limit(limit)
        )
        with self.session_factory() as session:
            rows = session.scalars(statement).all()
            return [self._to_record(row) for row in rows]

    def count_actions(self) -> int:
        """Count action records."""
        with self.session_factory() as session:
            return len(session.scalars(select(AutomationActionLog)).all())

    def _to_record(self, log: AutomationActionLog) -> AutomationActionRecord:
        return AutomationActionRecord(
            id=log.id,
            tool_name=log.tool_name,
            parameters=json.loads(log.parameters_json or "{}"),
            safety_level=log.safety_level,
            permission_status=log.permission_status,
            success=log.success,
            message=log.message,
            error_message=log.error_message,
            started_at=log.started_at,
            completed_at=log.completed_at,
            duration_seconds=log.duration_seconds,
        )

    def _duration_seconds(self, started_at: datetime, ended_at: datetime) -> float:
        if started_at.tzinfo is None and ended_at.tzinfo is not None:
            ended_at = ended_at.replace(tzinfo=None)
        if started_at.tzinfo is not None and ended_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=None)
        return max((ended_at - started_at).total_seconds(), 0.0)
