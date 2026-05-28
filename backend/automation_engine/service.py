"""Automation engine for desktop actions.

PyAutoGUI is imported lazily so Cherry AI can start in environments where GUI
automation is unavailable, such as future CI or containerized worker processes.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings


@dataclass
class AutomationEngine:
    """Coordinates safe desktop automation primitives."""

    settings: AppSettings

    def configure_pyautogui(self) -> None:
        """Apply project-level PyAutoGUI safety settings."""
        import pyautogui

        pyautogui.FAILSAFE = self.settings.pyautogui_failsafe
        pyautogui.PAUSE = self.settings.pyautogui_pause_seconds
