"""Enums for model routing — task types, modalities, routing modes."""

from __future__ import annotations

from enum import StrEnum


class TaskType(StrEnum):
    """Detected task type for model routing. Used by PromptClassifier and ModelRouter.

    Attributes:
        CODE: Code generation, debugging, review, implementation.
        GENERAL: General conversation, Q&A, chitchat.
        VISION: Image understanding, OCR, image description.
        VIDEO: Video analysis, video generation.
        PLANNING: Complex reasoning, task decomposition, strategy.
        REASONING: Math, logic, analytical reasoning.
        CREATIVE: Writing, brainstorming, creative content.
        TRANSLATION: Language translation.
    """

    CODE = "code"
    GENERAL = "general"
    VISION = "vision"
    VIDEO = "video"
    PLANNING = "planning"
    REASONING = "reasoning"
    CREATIVE = "creative"
    TRANSLATION = "translation"


class Modality(StrEnum):
    """Generic enum for content and model capabilities. Use for message content detection
    and model input/output capabilities (ModelProfile.modality_input, modality_output).

    Attributes:
        TEXT: Plain text.
        IMAGE: Image input/output.
        VIDEO: Video input/output.
        AUDIO: Audio input/output.
        FILE: Generic file attachment (for future extensibility).
    """

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"


class ComplexityTier(StrEnum):
    """Prompt complexity tier for model selection. Higher = prefer premium model.

    Attributes:
        LOW: Simple prompts — use cheaper models.
        MEDIUM: Moderate complexity — balance cost/capability.
        HIGH: Complex prompts — prefer premium models.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RoutingMode(StrEnum):
    """How the router selects among capable models.

    Attributes:
        AUTO: Intelligent auto-selection balancing cost and capability (default).
        COST_FIRST: Always use cheapest capable model.
        QUALITY_FIRST: Always use highest-priority capable model.
        MANUAL: Developer provides task type; no auto-classification.
    """

    AUTO = "auto"
    COST_FIRST = "cost_first"
    QUALITY_FIRST = "quality_first"
    MANUAL = "manual"
