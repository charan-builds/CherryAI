"""Typed structured configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field

PROFILE_DEVELOPMENT = "development"
PROFILE_PRODUCTION = "production"
PROFILE_DEBUG = "debug"
SUPPORTED_PROFILES = {PROFILE_DEVELOPMENT, PROFILE_PRODUCTION, PROFILE_DEBUG, "test"}


@dataclass(frozen=True)
class AIConfig:
    """AI runtime configuration."""

    ollama_host: str
    model: str
    timeout_seconds: float
    max_retries: int


@dataclass(frozen=True)
class ObserverConfig:
    """Observer engine configuration."""

    enabled: bool
    poll_interval_seconds: float
    idle_threshold_seconds: float
    distraction_keywords: tuple[str, ...]


@dataclass(frozen=True)
class AutomationConfig:
    """Automation safety and timeout configuration."""

    enabled: bool
    timeout_seconds: float
    pyautogui_failsafe: bool
    pyautogui_pause_seconds: float


@dataclass(frozen=True)
class WorkflowConfig:
    """Workflow execution configuration."""

    default_retries: int
    max_retries: int
    step_timeout_seconds: float
    max_steps: int
    ai_planning_enabled: bool
    scheduler_poll_seconds: float


@dataclass(frozen=True)
class NotificationConfig:
    """Notification configuration."""

    global_cooldown_seconds: float
    duplicate_window_seconds: float
    quiet_mode_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str


@dataclass(frozen=True)
class MemoryConfig:
    """Memory subsystem configuration."""

    enabled: bool
    context_max_chars: int
    retention_days: int
    working_memory_ttl_minutes: int


@dataclass(frozen=True)
class LoggingConfig:
    """Logging and diagnostics configuration."""

    level: str
    sql_echo: bool
    structured_logs_enabled: bool = True


@dataclass(frozen=True)
class PerformanceConfig:
    """Performance monitor configuration."""

    monitor_enabled: bool = True
    sample_interval_seconds: float = 5.0
    memory_warning_mb: float = 1024.0
    event_rate_warning_per_minute: int = 600


@dataclass(frozen=True)
class FeatureFlags:
    """Runtime feature flags."""

    proactive_enabled: bool = True
    automation_enabled: bool = True
    workflows_enabled: bool = True
    safe_mode_default: bool = False


@dataclass(frozen=True)
class StructuredAppConfig:
    """Grouped configuration object for platform services."""

    profile: str
    ai: AIConfig
    observer: ObserverConfig
    automation: AutomationConfig
    workflows: WorkflowConfig
    notifications: NotificationConfig
    memory: MemoryConfig
    logging: LoggingConfig
    performance: PerformanceConfig
    feature_flags: FeatureFlags


@dataclass(frozen=True)
class ConfigValidationResult:
    """Validation result for structured configuration."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
