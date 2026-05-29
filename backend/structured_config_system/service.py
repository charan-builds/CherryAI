"""Structured configuration loader and validator."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.structured_config_system.schemas import (
    SUPPORTED_PROFILES,
    AIConfig,
    AutomationConfig,
    ConfigValidationResult,
    FeatureFlags,
    LoggingConfig,
    MemoryConfig,
    NotificationConfig,
    ObserverConfig,
    PerformanceConfig,
    StructuredAppConfig,
    WorkflowConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class StructuredConfigSystem:
    """Builds validated grouped configuration from AppSettings."""

    settings: AppSettings
    current_config: StructuredAppConfig | None = None

    def load(self) -> StructuredAppConfig:
        """Create and validate structured configuration."""
        config = self._from_settings(self.settings)
        validation = self.validate(config)
        if not validation.is_valid:
            logger.warning("Config validation failed: %s", validation.errors)
            config = self._safe_fallback(config)
        for warning in validation.warnings:
            logger.info("Config warning: %s", warning)
        self.current_config = config
        return config

    def reload(self, settings: AppSettings | None = None) -> StructuredAppConfig:
        """Reload configuration from updated settings."""
        if settings is not None:
            self.settings = settings
        return self.load()

    def validate(self, config: StructuredAppConfig) -> ConfigValidationResult:
        """Validate typed configuration groups."""
        errors: list[str] = []
        warnings: list[str] = []

        if config.profile not in SUPPORTED_PROFILES:
            errors.append(f"Unsupported profile: {config.profile}")
        if config.ai.timeout_seconds <= 0:
            errors.append("AI timeout must be positive.")
        if config.ai.max_retries < 0:
            errors.append("AI retries cannot be negative.")
        if config.observer.poll_interval_seconds <= 0:
            errors.append("Observer poll interval must be positive.")
        if config.automation.timeout_seconds <= 0:
            errors.append("Automation timeout must be positive.")
        if config.workflows.max_retries < config.workflows.default_retries:
            errors.append("Workflow max retries cannot be below default retries.")
        if config.workflows.max_steps <= 0:
            errors.append("Workflow max steps must be positive.")
        if config.performance.sample_interval_seconds <= 0:
            errors.append("Performance sample interval must be positive.")

        if config.profile == "production" and config.logging.level == "DEBUG":
            warnings.append("Production profile is using DEBUG logging.")
        if not config.automation.pyautogui_failsafe:
            warnings.append("PyAutoGUI failsafe is disabled.")

        return ConfigValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def feature_enabled(self, name: str) -> bool:
        """Return one feature flag by name with safe fallback."""
        config = self.current_config or self.load()
        return bool(getattr(config.feature_flags, name, False))

    def _from_settings(self, settings: AppSettings) -> StructuredAppConfig:
        return StructuredAppConfig(
            profile=settings.app_env,
            ai=AIConfig(
                ollama_host=settings.ollama_host,
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
                max_retries=settings.ollama_max_retries,
            ),
            observer=ObserverConfig(
                enabled=settings.observer_enabled,
                poll_interval_seconds=settings.observer_poll_interval_seconds,
                idle_threshold_seconds=settings.idle_threshold_seconds,
                distraction_keywords=settings.distraction_keywords,
            ),
            automation=AutomationConfig(
                enabled=settings.automation_enabled,
                timeout_seconds=settings.automation_timeout_seconds,
                pyautogui_failsafe=settings.pyautogui_failsafe,
                pyautogui_pause_seconds=settings.pyautogui_pause_seconds,
            ),
            workflows=WorkflowConfig(
                default_retries=settings.workflow_default_retries,
                max_retries=settings.workflow_max_retries,
                step_timeout_seconds=settings.workflow_step_timeout_seconds,
                max_steps=settings.workflow_max_steps,
                ai_planning_enabled=settings.workflow_ai_planning_enabled,
                scheduler_poll_seconds=settings.workflow_scheduler_poll_seconds,
            ),
            notifications=NotificationConfig(
                global_cooldown_seconds=settings.notification_global_cooldown_seconds,
                duplicate_window_seconds=settings.notification_duplicate_window_seconds,
                quiet_mode_enabled=settings.notification_quiet_mode_enabled,
                quiet_hours_start=settings.notification_quiet_hours_start,
                quiet_hours_end=settings.notification_quiet_hours_end,
            ),
            memory=MemoryConfig(
                enabled=settings.memory_enabled,
                context_max_chars=settings.memory_context_max_chars,
                retention_days=settings.memory_retention_days,
                working_memory_ttl_minutes=settings.working_memory_ttl_minutes,
            ),
            logging=LoggingConfig(
                level=settings.log_level,
                sql_echo=settings.sql_echo,
            ),
            performance=PerformanceConfig(
                sample_interval_seconds=settings.performance_monitor_interval_seconds,
                memory_warning_mb=settings.performance_memory_warning_mb,
                event_rate_warning_per_minute=settings.performance_event_rate_warning_per_minute,
            ),
            feature_flags=FeatureFlags(
                proactive_enabled=settings.proactive_enabled,
                automation_enabled=settings.automation_enabled,
                workflows_enabled=True,
                safe_mode_default=settings.sandbox_safe_mode_default,
            ),
        )

    def _safe_fallback(self, config: StructuredAppConfig) -> StructuredAppConfig:
        return StructuredAppConfig(
            profile="development",
            ai=AIConfig(
                ollama_host=config.ai.ollama_host or "http://localhost:11434",
                model=config.ai.model or "llama3.1",
                timeout_seconds=max(config.ai.timeout_seconds, 1.0),
                max_retries=max(config.ai.max_retries, 0),
            ),
            observer=ObserverConfig(
                enabled=config.observer.enabled,
                poll_interval_seconds=max(config.observer.poll_interval_seconds, 0.25),
                idle_threshold_seconds=max(config.observer.idle_threshold_seconds, 1.0),
                distraction_keywords=config.observer.distraction_keywords,
            ),
            automation=AutomationConfig(
                enabled=False,
                timeout_seconds=max(config.automation.timeout_seconds, 1.0),
                pyautogui_failsafe=True,
                pyautogui_pause_seconds=max(config.automation.pyautogui_pause_seconds, 0.05),
            ),
            workflows=WorkflowConfig(
                default_retries=0,
                max_retries=max(config.workflows.max_retries, 0),
                step_timeout_seconds=max(config.workflows.step_timeout_seconds, 1.0),
                max_steps=max(config.workflows.max_steps, 1),
                ai_planning_enabled=False,
                scheduler_poll_seconds=max(config.workflows.scheduler_poll_seconds, 1.0),
            ),
            notifications=config.notifications,
            memory=config.memory,
            logging=config.logging,
            performance=PerformanceConfig(),
            feature_flags=FeatureFlags(
                proactive_enabled=False,
                automation_enabled=False,
                workflows_enabled=True,
                safe_mode_default=True,
            ),
        )
