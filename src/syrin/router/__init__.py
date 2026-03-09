"""Model routing — task classification, modality detection, intelligent model selection."""

from syrin.router.classifier import (
    ClassificationResult,
    EmbeddingClassifier,
    PromptClassifier,
)
from syrin.router.config import RouterConfig
from syrin.router.defaults import DEFAULT_PROFILES
from syrin.router.enums import ComplexityTier, Modality, RoutingMode, TaskType
from syrin.router.modality import ModalityDetector
from syrin.router.profile import ModelProfile
from syrin.router.router import ModelRouter, RoutingReason

__all__ = [
    "ClassificationResult",
    "ComplexityTier",
    "DEFAULT_PROFILES",
    "EmbeddingClassifier",
    "Modality",
    "ModelProfile",
    "ModelRouter",
    "ModalityDetector",
    "PromptClassifier",
    "RouterConfig",
    "RoutingMode",
    "RoutingReason",
    "TaskType",
]
