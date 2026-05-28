"""Environment-driven settings for Cherry AI.

The app is local-first, so defaults are safe for a developer workstation.
Environment variables provide the boundary for future installers, Docker
images, and per-user overrides.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - only used before dependencies install
    load_dotenv = None

from utils.paths import get_project_root


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class AppSettings:
    """Typed runtime settings shared across the application."""

    app_name: str
    app_env: str
    debug: bool
    log_level: str
    sql_echo: bool
    project_root: Path
    data_dir: Path
    logs_dir: Path
    database_url: str
    ollama_host: str
    ollama_model: str
    ollama_timeout_seconds: float
    ollama_max_retries: int
    pyautogui_failsafe: bool
    pyautogui_pause_seconds: float
    observer_enabled: bool
    observer_poll_interval_seconds: float
    idle_threshold_seconds: float
    distraction_keywords: tuple[str, ...]


def load_settings() -> AppSettings:
    """Load settings from .env and process environment variables."""
    project_root = Path(os.getenv("CHERRY_PROJECT_ROOT", get_project_root())).resolve()

    env_file = project_root / ".env"
    if load_dotenv is not None and env_file.exists():
        load_dotenv(env_file)

    data_dir = Path(os.getenv("CHERRY_DATA_DIR", project_root / ".cherry_data")).resolve()
    logs_dir = project_root / "logs"
    default_database_url = f"sqlite:///{(data_dir / 'cherry_ai.db').as_posix()}"

    return AppSettings(
        app_name="Cherry AI",
        app_env=os.getenv("CHERRY_APP_ENV", "development"),
        debug=_as_bool(os.getenv("CHERRY_DEBUG"), default=True),
        log_level=os.getenv("CHERRY_LOG_LEVEL", "INFO").upper(),
        sql_echo=_as_bool(os.getenv("CHERRY_SQL_ECHO"), default=False),
        project_root=project_root,
        data_dir=data_dir,
        logs_dir=logs_dir,
        database_url=os.getenv("CHERRY_DATABASE_URL", default_database_url),
        ollama_host=os.getenv("CHERRY_OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("CHERRY_OLLAMA_MODEL", "llama3.1"),
        ollama_timeout_seconds=_as_float(
            os.getenv("CHERRY_OLLAMA_TIMEOUT_SECONDS"),
            default=30.0,
        ),
        ollama_max_retries=_as_int(
            os.getenv("CHERRY_OLLAMA_MAX_RETRIES"),
            default=1,
        ),
        pyautogui_failsafe=_as_bool(
            os.getenv("CHERRY_PYAUTOGUI_FAILSAFE"),
            default=True,
        ),
        pyautogui_pause_seconds=_as_float(
            os.getenv("CHERRY_PYAUTOGUI_PAUSE_SECONDS"),
            default=0.1,
        ),
        observer_enabled=_as_bool(
            os.getenv("CHERRY_OBSERVER_ENABLED"),
            default=True,
        ),
        observer_poll_interval_seconds=_as_float(
            os.getenv("CHERRY_OBSERVER_POLL_INTERVAL_SECONDS"),
            default=2.0,
        ),
        idle_threshold_seconds=_as_float(
            os.getenv("CHERRY_IDLE_THRESHOLD_SECONDS"),
            default=300.0,
        ),
        distraction_keywords=tuple(
            keyword.strip()
            for keyword in os.getenv(
                "CHERRY_DISTRACTION_KEYWORDS",
                "YouTube,Netflix,Instagram,TikTok,Reddit",
            ).split(",")
            if keyword.strip()
        ),
    )
