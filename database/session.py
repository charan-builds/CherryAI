"""Database engine and session helpers."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import AppSettings


def create_database_engine(settings: AppSettings) -> Engine:
    """Create a SQLAlchemy engine from application settings."""
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=settings.sql_echo,
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker:
    """Create a configured session factory."""
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
