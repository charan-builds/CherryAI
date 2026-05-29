"""Workflow validation schemas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkflowValidationResult:
    """Result of validating a workflow plan."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def message(self) -> str:
        """Return a compact validation summary."""
        if self.is_valid:
            return "Workflow plan is valid."
        return "; ".join(self.errors)
