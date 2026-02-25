"""Guardrail check result - return type for sync check() calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardrailCheckResult:
    """Result of guardrail check (sync API).

    Returned by GuardrailChain.check() and used when the agent runs
    guardrails during a request.
    """

    passed: bool
    """Whether the guardrail check passed."""
    reason: str | None = None
    """Human-readable reason if failed."""
    metadata: dict[str, Any] = field(default_factory=dict)
    """Arbitrary metadata about the check."""


__all__ = ["GuardrailCheckResult"]
