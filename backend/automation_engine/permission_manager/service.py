"""Permission checks for automation tools."""

from __future__ import annotations

from dataclasses import dataclass

from backend.automation_engine.schemas import (
    PERMISSION_ALLOWED,
    PERMISSION_BLOCKED,
    PERMISSION_CONFIRMATION_REQUIRED,
    SAFETY_HIGH,
    SAFETY_MEDIUM,
    SAFETY_SAFE,
    AutomationTool,
    PermissionDecision,
)


BLOCKED_KEYWORDS = (
    "delete",
    "format",
    "shutdown",
    "restart",
    "registry",
    "regedit",
    "powershell",
    "cmd.exe",
    "remove-item",
    "rm ",
)


@dataclass
class PermissionManager:
    """Applies safety policy before automation tools execute."""

    def evaluate(
        self,
        tool: AutomationTool,
        parameters: dict[str, object],
        confirmed: bool = False,
    ) -> PermissionDecision:
        """Return whether the tool execution is allowed."""
        unsafe_match = self._find_blocked_keyword(parameters)
        if unsafe_match:
            return PermissionDecision(
                status=PERMISSION_BLOCKED,
                reason=f"Blocked unsafe automation request containing '{unsafe_match}'.",
            )

        if tool.safety_level == SAFETY_SAFE:
            return PermissionDecision(
                status=PERMISSION_ALLOWED,
                reason="Safe automation action auto-allowed.",
            )

        if tool.safety_level == SAFETY_MEDIUM and confirmed:
            return PermissionDecision(
                status=PERMISSION_ALLOWED,
                reason="Medium-risk action confirmed by user.",
            )

        if tool.safety_level == SAFETY_MEDIUM:
            return PermissionDecision(
                status=PERMISSION_CONFIRMATION_REQUIRED,
                reason="Medium-risk automation action requires confirmation.",
            )

        if tool.safety_level == SAFETY_HIGH:
            return PermissionDecision(
                status=PERMISSION_BLOCKED,
                reason="High-risk automation actions are blocked.",
            )

        return PermissionDecision(
            status=PERMISSION_BLOCKED,
            reason=f"Unknown safety level: {tool.safety_level}.",
        )

    def _find_blocked_keyword(self, parameters: dict[str, object]) -> str:
        haystack = " ".join(str(value).lower() for value in parameters.values())
        for keyword in BLOCKED_KEYWORDS:
            if keyword in haystack:
                return keyword.strip()
        return ""
