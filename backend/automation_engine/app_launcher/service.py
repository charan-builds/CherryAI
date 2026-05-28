"""Windows-compatible application launcher."""

from __future__ import annotations

import logging
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from config.settings import AppSettings
from backend.automation_engine.schemas import ToolExecutionResult

logger = logging.getLogger(__name__)


DEFAULT_APP_MAPPINGS = {
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "chrome": "chrome",
    "google chrome": "chrome",
    "file explorer": "explorer",
    "explorer": "explorer",
    "jupyter": "jupyter notebook",
    "jupyter notebook": "jupyter notebook",
}


ProcessRunner = Callable[[list[str]], None]


@dataclass
class AppLauncher:
    """Launches configured local applications."""

    settings: AppSettings
    runner: ProcessRunner | None = None

    def __post_init__(self) -> None:
        mappings = dict(DEFAULT_APP_MAPPINGS)
        mappings.update(self.settings.custom_app_mappings)
        self.app_mappings = mappings

    def launch(self, app_name: str) -> ToolExecutionResult:
        """Launch a known app alias."""
        alias = app_name.strip().lower()
        command = self.app_mappings.get(alias)
        if not command:
            return ToolExecutionResult(
                success=False,
                message=f"I do not know how to launch '{app_name}'.",
                error_message="Unknown app alias.",
            )

        args = self._command_to_args(command)
        try:
            logger.info("Launching app %s using %s", alias, args)
            if self.runner is not None:
                self.runner(args)
            else:
                subprocess.Popen(  # noqa: S603 - command comes from allowlisted mapping
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                )
            return ToolExecutionResult(
                success=True,
                message=f"Opened {app_name}.",
                data={"app_name": app_name, "command": command},
            )
        except Exception as exc:
            logger.exception("Failed to launch app: %s", app_name)
            return ToolExecutionResult(
                success=False,
                message=f"I could not open {app_name}.",
                error_message=str(exc),
            )

    def _command_to_args(self, command: str) -> list[str]:
        command_path = Path(command)
        if command_path.exists():
            return [str(command_path)]
        return shlex.split(command, posix=False)
