"""Protocols for routing — pluggable classifiers and embedding providers."""

from __future__ import annotations

from typing import Protocol

from syrin.router.classifier import ClassificationResult
from syrin.router.enums import TaskType


class ClassifierProtocol(Protocol):
    """Protocol for task classifiers. Implement to plug in custom classifiers (LLM, BERT, regex)."""

    low_confidence_fallback: TaskType

    def classify(self, prompt: str) -> tuple[TaskType, float]:
        """Classify prompt into task type and confidence [0,1]."""
        ...

    def classify_extended(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ClassificationResult:
        """Extended classification with complexity and system alignment. Optional."""
        ...
