"""Agent integration helpers — build router and profiles from model lists."""

from __future__ import annotations

from typing import TYPE_CHECKING

from syrin.model import Model

if TYPE_CHECKING:
    from syrin.budget import Budget
from syrin.router.config import RouterConfig
from syrin.router.enums import Modality, TaskType
from syrin.router.profile import ModelProfile
from syrin.router.router import ModelRouter


def profiles_from_models(
    models: list[Model],
    *,
    strengths: list[TaskType] | None = None,
) -> list[ModelProfile]:
    """Build ModelProfile list from a list of models for simple routing.

    Each model gets a profile with:
    - name: model.name or model_id suffix
    - strengths: TaskType.GENERAL by default (capable of all), or provided list
    - modality_input/output: {Modality.TEXT}
    - supports_tools: True
    - priority: 100 (equal unless overridden)

    Use when passing model=[M1, M2, M3] to Agent without explicit profiles.
    For specialized routing (code vs vision), use ModelProfile directly.

    Args:
        models: List of Model instances.
        strengths: Task types each model supports. Default [TaskType.GENERAL].

    Returns:
        List of ModelProfile, one per model.

    Example:
        profiles = profiles_from_models([
            Model.OpenAI("gpt-4o-mini"),
            Model.Anthropic("claude-sonnet"),
        ])
        router = ModelRouter(profiles=profiles)
    """
    if not models:
        return []
    task_strengths = strengths or [TaskType.GENERAL]
    out: list[ModelProfile] = []
    seen: set[str] = set()
    for i, m in enumerate(models):
        name = getattr(m, "name", None) or getattr(m, "model_id", "")
        if not name and hasattr(m, "_name"):
            name = getattr(m, "_name", "")
        if not name and hasattr(m, "_model_id"):
            raw = getattr(m, "_model_id", "")
            name = raw.split("/")[-1] if "/" in raw else raw
        if not name:
            name = f"model-{i}"
        base = name
        idx = 0
        while name in seen:
            idx += 1
            name = f"{base}-{idx}"
        seen.add(name)
        out.append(
            ModelProfile(
                model=m,
                name=name,
                strengths=list(task_strengths),
                modality_input={Modality.TEXT},
                modality_output={Modality.TEXT},
                supports_tools=True,
                priority=100,
            )
        )
    return out


def build_router_from_models(
    models: list[Model],
    *,
    router_config: RouterConfig | None = None,
    budget: Budget | None = None,
) -> ModelRouter:
    """Build a ModelRouter from a list of models and optional RouterConfig.

    When router_config is provided, its routing_mode, force_model, budget
    thresholds, etc. are applied. Otherwise defaults are used.

    Args:
        models: List of Model instances.
        router_config: Optional RouterConfig for routing behavior.
        budget: Optional Budget for cost-aware routing.

    Returns:
        ModelRouter ready for Agent use.
    """
    profiles = profiles_from_models(models)
    if router_config is not None:
        if router_config.router is not None:
            return router_config.router
        return ModelRouter(
            profiles=router_config.profiles or profiles,
            routing_mode=router_config.routing_mode,
            classifier=router_config.classifier,
            budget=budget,
            budget_optimisation=router_config.budget_optimisation,
            economy_at=router_config.economy_at,
            cheapest_at=router_config.cheapest_at,
            force_model=router_config.force_model,
            routing_rule_callback=router_config.routing_rule_callback,
        )
    return ModelRouter(profiles=profiles, budget=budget)
