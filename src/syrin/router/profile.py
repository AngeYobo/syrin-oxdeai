"""ModelProfile — model capability profile for routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from syrin.router.enums import Modality, TaskType

if TYPE_CHECKING:
    from syrin.model import Model


@dataclass
class ModelProfile:
    """Capability profile for a model. Used by ModelRouter to select the best model.

    Attributes:
        model: The Model instance (has pricing).
        name: Display name (e.g., "claude-code").
        strengths: Task types this model is good at.
        modality_input: Input modalities supported (TEXT, IMAGE, etc.).
        modality_output: Output modalities supported.
        supports_tools: If False, exclude when tools are present.
        priority: Higher = preferred when routing (default 100).
    """

    model: Model
    name: str
    strengths: list[TaskType]
    modality_input: set[Modality] | None = None
    modality_output: set[Modality] | None = None
    supports_tools: bool = True
    priority: int = 100

    def __post_init__(self) -> None:
        if not self.strengths:
            raise ValueError(
                "ModelProfile.strengths must be non-empty. "
                "Add at least one TaskType (e.g., [TaskType.CODE])."
            )
        if not (self.name and self.name.strip()):
            raise ValueError(
                "ModelProfile.name must be non-empty. Use a display name (e.g., 'claude-code')."
            )
        if self.priority < 0:
            raise ValueError(
                f"ModelProfile.priority must be >= 0; got {self.priority}. "
                "Higher priority = preferred when routing."
            )
        if self.modality_input is None:
            object.__setattr__(self, "modality_input", {Modality.TEXT})
        if self.modality_output is None:
            object.__setattr__(self, "modality_output", {Modality.TEXT})
