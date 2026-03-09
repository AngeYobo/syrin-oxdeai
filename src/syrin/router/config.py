"""RouterConfig — configuration for model selection and routing."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, Field, model_validator

from syrin.model import Model
from syrin.router.classifier import PromptClassifier
from syrin.router.enums import RoutingMode, TaskType
from syrin.router.profile import ModelProfile

# Import last to avoid circular: ModelRouter imports classifier, profile, etc.
from syrin.router.router import ModelRouter


class RouterConfig(BaseModel):
    """Configuration for model selection and routing. Use with Agent(router_config=...).

    Attributes:
        router: Explicit ModelRouter. If set, overrides auto-created router from model list.
        classifier: Custom PromptClassifier. None = use default (embeddings).
        routing_mode: AUTO, COST_FIRST, QUALITY_FIRST, or MANUAL.
        force_model: Bypass routing; always use this model.
        budget_optimisation: When True, prefer cheaper models when budget runs low.
        economy_at: Fraction (0–1). When remaining/limit < this, prefer cheaper capable models.
        cheapest_at: Fraction (0–1). When remaining/limit < this, force cheapest capable model.
        max_cost_per_1k_tokens: Cap on cost per 1K tokens when selecting models.
        profiles: Custom profiles (override auto-generated from model list).
        routing_rule_callback: Custom callback(prompt, task_type, profile_names) -> profile_name | None.
    """

    model_config = {"arbitrary_types_allowed": True}

    router: ModelRouter | None = Field(
        default=None,
        description="Explicit ModelRouter. Overrides auto-created router from model list.",
    )
    classifier: PromptClassifier | None = Field(
        default=None,
        description="Custom PromptClassifier. None = default embeddings-based.",
    )
    routing_mode: RoutingMode = Field(
        default=RoutingMode.AUTO,
        description="AUTO, COST_FIRST, QUALITY_FIRST, or MANUAL.",
    )
    force_model: Model | None = Field(
        default=None,
        description="Bypass routing; always use this model.",
    )
    budget_optimisation: bool = Field(
        default=True,
        description="When True, prefer cheaper models when budget runs low (use economy_at and cheapest_at).",
    )
    economy_at: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction (0–1) of remaining budget. When remaining/limit < this, "
            "router prefers cheaper capable models. Default 0.20."
        ),
    )
    cheapest_at: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction (0–1) of remaining budget. When remaining/limit < this, "
            "router forces cheapest capable model. Default 0.10. Must be <= economy_at."
        ),
    )
    max_cost_per_1k_tokens: float | None = Field(
        default=None,
        ge=0.0,
        description="Max cost per 1K tokens when selecting models. None = no cap.",
    )
    profiles: list[ModelProfile] | None = Field(
        default=None,
        description="Custom profiles. Override auto-generated from model list.",
    )
    routing_rule_callback: Callable[[str, TaskType, list[str]], str | None] | None = Field(
        default=None,
        description="Callback(prompt, task_type, profile_names) -> preferred profile name or None.",
    )

    @model_validator(mode="after")
    def _validate_cheapest_le_economy(self) -> RouterConfig:
        if self.cheapest_at > self.economy_at:
            raise ValueError(
                f"cheapest_at ({self.cheapest_at}) must be <= economy_at ({self.economy_at}). "
                "Adjust RouterConfig."
            )
        return self


# Resolve forward refs (Model, ModelRouter, etc.) after all types are imported
RouterConfig.model_rebuild()
