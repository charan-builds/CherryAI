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
    automation_enabled: bool
    automation_timeout_seconds: float
    screenshot_dir: Path
    custom_app_mappings: dict[str, str]
    proactive_enabled: bool = True
    proactive_refresh_interval_seconds: float = 30.0
    productivity_daily_task_target: int = 3
    productivity_daily_study_target_minutes: int = 90
    focus_target_minutes: int = 45
    focus_break_after_minutes: int = 50
    distraction_threshold: int = 3
    recommendation_cooldown_seconds: float = 900.0
    notification_global_cooldown_seconds: float = 300.0
    notification_duplicate_window_seconds: float = 1800.0
    notification_quiet_mode_enabled: bool = True
    notification_quiet_hours_start: str = "22:00"
    notification_quiet_hours_end: str = "07:00"
    memory_enabled: bool = True
    memory_recent_task_limit: int = 5
    memory_recent_interaction_limit: int = 6
    memory_behavioral_pattern_limit: int = 5
    memory_productivity_summary_limit: int = 3
    memory_context_max_chars: int = 1800
    memory_retention_days: int = 180
    working_memory_ttl_minutes: int = 240
    semantic_memory_min_confidence: float = 0.35
    memory_prune_batch_size: int = 100
    workflow_default_retries: int = 1
    workflow_max_retries: int = 3
    workflow_step_timeout_seconds: float = 15.0
    workflow_max_steps: int = 20
    workflow_ai_planning_enabled: bool = False
    workflow_scheduler_poll_seconds: float = 30.0
    performance_monitor_interval_seconds: float = 5.0
    performance_memory_warning_mb: float = 1024.0
    performance_event_rate_warning_per_minute: int = 600
    sandbox_safe_mode_default: bool = False
    sandbox_emergency_stop_default: bool = False
    sandbox_rate_limit_max_calls: int = 20
    sandbox_rate_limit_window_seconds: float = 60.0
    user_display_name: str = "Charan"
    companion_enabled: bool = True
    companion_message_cooldown_seconds: float = 1800.0
    companion_briefing_refresh_minutes: int = 60
    personal_os_snapshot_interval_seconds: float = 60.0
    knowledge_memory_enabled: bool = True
    knowledge_max_text_chars: int = 120000
    knowledge_project_file_limit: int = 80
    knowledge_ocr_sidecar_enabled: bool = True


def load_settings() -> AppSettings:
    """Load settings from .env and process environment variables."""
    project_root = Path(os.getenv("CHERRY_PROJECT_ROOT", get_project_root())).resolve()

    env_file = project_root / ".env"
    if load_dotenv is not None and env_file.exists():
        load_dotenv(env_file)

    data_dir = Path(os.getenv("CHERRY_DATA_DIR", project_root / ".cherry_data")).resolve()
    logs_dir = project_root / "logs"
    default_database_url = f"sqlite:///{(data_dir / 'cherry_ai.db').as_posix()}"

    screenshot_dir = Path(
        os.getenv("CHERRY_SCREENSHOT_DIR", data_dir / "screenshots")
    ).resolve()

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
        automation_enabled=_as_bool(
            os.getenv("CHERRY_AUTOMATION_ENABLED"),
            default=True,
        ),
        automation_timeout_seconds=_as_float(
            os.getenv("CHERRY_AUTOMATION_TIMEOUT_SECONDS"),
            default=10.0,
        ),
        screenshot_dir=screenshot_dir,
        custom_app_mappings=_parse_app_mappings(
            os.getenv("CHERRY_CUSTOM_APP_MAPPINGS", "")
        ),
        proactive_enabled=_as_bool(
            os.getenv("CHERRY_PROACTIVE_ENABLED"),
            default=True,
        ),
        proactive_refresh_interval_seconds=_as_float(
            os.getenv("CHERRY_PROACTIVE_REFRESH_INTERVAL_SECONDS"),
            default=30.0,
        ),
        productivity_daily_task_target=_as_int(
            os.getenv("CHERRY_PRODUCTIVITY_DAILY_TASK_TARGET"),
            default=3,
        ),
        productivity_daily_study_target_minutes=_as_int(
            os.getenv("CHERRY_PRODUCTIVITY_DAILY_STUDY_TARGET_MINUTES"),
            default=90,
        ),
        focus_target_minutes=_as_int(
            os.getenv("CHERRY_FOCUS_TARGET_MINUTES"),
            default=45,
        ),
        focus_break_after_minutes=_as_int(
            os.getenv("CHERRY_FOCUS_BREAK_AFTER_MINUTES"),
            default=50,
        ),
        distraction_threshold=_as_int(
            os.getenv("CHERRY_DISTRACTION_THRESHOLD"),
            default=3,
        ),
        recommendation_cooldown_seconds=_as_float(
            os.getenv("CHERRY_RECOMMENDATION_COOLDOWN_SECONDS"),
            default=900.0,
        ),
        notification_global_cooldown_seconds=_as_float(
            os.getenv("CHERRY_NOTIFICATION_GLOBAL_COOLDOWN_SECONDS"),
            default=300.0,
        ),
        notification_duplicate_window_seconds=_as_float(
            os.getenv("CHERRY_NOTIFICATION_DUPLICATE_WINDOW_SECONDS"),
            default=1800.0,
        ),
        notification_quiet_mode_enabled=_as_bool(
            os.getenv("CHERRY_NOTIFICATION_QUIET_MODE_ENABLED"),
            default=True,
        ),
        notification_quiet_hours_start=os.getenv(
            "CHERRY_NOTIFICATION_QUIET_HOURS_START",
            "22:00",
        ),
        notification_quiet_hours_end=os.getenv(
            "CHERRY_NOTIFICATION_QUIET_HOURS_END",
            "07:00",
        ),
        memory_enabled=_as_bool(
            os.getenv("CHERRY_MEMORY_ENABLED"),
            default=True,
        ),
        memory_recent_task_limit=_as_int(
            os.getenv("CHERRY_MEMORY_RECENT_TASK_LIMIT"),
            default=5,
        ),
        memory_recent_interaction_limit=_as_int(
            os.getenv("CHERRY_MEMORY_RECENT_INTERACTION_LIMIT"),
            default=6,
        ),
        memory_behavioral_pattern_limit=_as_int(
            os.getenv("CHERRY_MEMORY_BEHAVIORAL_PATTERN_LIMIT"),
            default=5,
        ),
        memory_productivity_summary_limit=_as_int(
            os.getenv("CHERRY_MEMORY_PRODUCTIVITY_SUMMARY_LIMIT"),
            default=3,
        ),
        memory_context_max_chars=_as_int(
            os.getenv("CHERRY_MEMORY_CONTEXT_MAX_CHARS"),
            default=1800,
        ),
        memory_retention_days=_as_int(
            os.getenv("CHERRY_MEMORY_RETENTION_DAYS"),
            default=180,
        ),
        working_memory_ttl_minutes=_as_int(
            os.getenv("CHERRY_WORKING_MEMORY_TTL_MINUTES"),
            default=240,
        ),
        semantic_memory_min_confidence=_as_float(
            os.getenv("CHERRY_SEMANTIC_MEMORY_MIN_CONFIDENCE"),
            default=0.35,
        ),
        memory_prune_batch_size=_as_int(
            os.getenv("CHERRY_MEMORY_PRUNE_BATCH_SIZE"),
            default=100,
        ),
        workflow_default_retries=_as_int(
            os.getenv("CHERRY_WORKFLOW_DEFAULT_RETRIES"),
            default=1,
        ),
        workflow_max_retries=_as_int(
            os.getenv("CHERRY_WORKFLOW_MAX_RETRIES"),
            default=3,
        ),
        workflow_step_timeout_seconds=_as_float(
            os.getenv("CHERRY_WORKFLOW_STEP_TIMEOUT_SECONDS"),
            default=15.0,
        ),
        workflow_max_steps=_as_int(
            os.getenv("CHERRY_WORKFLOW_MAX_STEPS"),
            default=20,
        ),
        workflow_ai_planning_enabled=_as_bool(
            os.getenv("CHERRY_WORKFLOW_AI_PLANNING_ENABLED"),
            default=False,
        ),
        workflow_scheduler_poll_seconds=_as_float(
            os.getenv("CHERRY_WORKFLOW_SCHEDULER_POLL_SECONDS"),
            default=30.0,
        ),
        performance_monitor_interval_seconds=_as_float(
            os.getenv("CHERRY_PERFORMANCE_MONITOR_INTERVAL_SECONDS"),
            default=5.0,
        ),
        performance_memory_warning_mb=_as_float(
            os.getenv("CHERRY_PERFORMANCE_MEMORY_WARNING_MB"),
            default=1024.0,
        ),
        performance_event_rate_warning_per_minute=_as_int(
            os.getenv("CHERRY_PERFORMANCE_EVENT_RATE_WARNING_PER_MINUTE"),
            default=600,
        ),
        sandbox_safe_mode_default=_as_bool(
            os.getenv("CHERRY_SANDBOX_SAFE_MODE_DEFAULT"),
            default=False,
        ),
        sandbox_emergency_stop_default=_as_bool(
            os.getenv("CHERRY_SANDBOX_EMERGENCY_STOP_DEFAULT"),
            default=False,
        ),
        sandbox_rate_limit_max_calls=_as_int(
            os.getenv("CHERRY_SANDBOX_RATE_LIMIT_MAX_CALLS"),
            default=20,
        ),
        sandbox_rate_limit_window_seconds=_as_float(
            os.getenv("CHERRY_SANDBOX_RATE_LIMIT_WINDOW_SECONDS"),
            default=60.0,
        ),
        user_display_name=os.getenv("CHERRY_USER_DISPLAY_NAME", "Charan").strip()
        or "there",
        companion_enabled=_as_bool(
            os.getenv("CHERRY_COMPANION_ENABLED"),
            default=True,
        ),
        companion_message_cooldown_seconds=_as_float(
            os.getenv("CHERRY_COMPANION_MESSAGE_COOLDOWN_SECONDS"),
            default=1800.0,
        ),
        companion_briefing_refresh_minutes=_as_int(
            os.getenv("CHERRY_COMPANION_BRIEFING_REFRESH_MINUTES"),
            default=60,
        ),
        personal_os_snapshot_interval_seconds=_as_float(
            os.getenv("CHERRY_PERSONAL_OS_SNAPSHOT_INTERVAL_SECONDS"),
            default=60.0,
        ),
        knowledge_memory_enabled=_as_bool(
            os.getenv("CHERRY_KNOWLEDGE_MEMORY_ENABLED"),
            default=True,
        ),
        knowledge_max_text_chars=_as_int(
            os.getenv("CHERRY_KNOWLEDGE_MAX_TEXT_CHARS"),
            default=120000,
        ),
        knowledge_project_file_limit=_as_int(
            os.getenv("CHERRY_KNOWLEDGE_PROJECT_FILE_LIMIT"),
            default=80,
        ),
        knowledge_ocr_sidecar_enabled=_as_bool(
            os.getenv("CHERRY_KNOWLEDGE_OCR_SIDECAR_ENABLED"),
            default=True,
        ),
    )


def _parse_app_mappings(raw_value: str) -> dict[str, str]:
    """Parse semicolon-separated app alias mappings."""
    mappings: dict[str, str] = {}
    for item in raw_value.split(";"):
        if "=" not in item:
            continue
        alias, command = item.split("=", 1)
        alias = alias.strip().lower()
        command = command.strip()
        if alias and command:
            mappings[alias] = command
    return mappings
