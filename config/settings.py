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
    pyautogui_failsafe: bool
    pyautogui_pause_seconds: float


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
        pyautogui_failsafe=_as_bool(
            os.getenv("CHERRY_PYAUTOGUI_FAILSAFE"),
            default=True,
        ),
        pyautogui_pause_seconds=_as_float(
            os.getenv("CHERRY_PYAUTOGUI_PAUSE_SECONDS"),
            default=0.1,
        ),
    )
