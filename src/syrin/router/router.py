"""ModelRouter and RoutingReason — intelligent model selection."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from syrin.budget import Budget
from syrin.cost import count_tokens
from syrin.exceptions import NoMatchingProfileError
from syrin.model import Model
from syrin.router.classifier import PromptClassifier
from syrin.router.enums import ComplexityTier, Modality, RoutingMode, TaskType
from syrin.router.modality import ModalityDetector
from syrin.router.profile import ModelProfile
from syrin.tool import ToolSpec
from syrin.types import Message

logger = logging.getLogger(__name__)


def _estimate_cost_for_profile(
    profile: ModelProfile,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate cost in USD for a profile given token counts."""
    model = profile.model
    pricing = model.get_pricing() if hasattr(model, "get_pricing") else None
    if pricing is None:
        return 0.0
    return round(
        (input_tokens / 1_000_000) * pricing.input_per_1m
        + (output_tokens / 1_000_000) * pricing.output_per_1m,
        6,
    )


@dataclass
class RoutingReason:
    """Explains why a model was selected. Returned by ModelRouter.route().

    Attributes:
        selected_model: Profile name chosen (e.g., "claude-code").
        task_type: Detected or overridden task type.
        reason: Human-readable explanation.
        cost_estimate: Estimated cost in USD for the call.
        alternatives: Other profile names that could have been used.
        classification_confidence: 0.0–1.0; confidence in task classification.
        complexity_tier: LOW/MEDIUM/HIGH when classify_extended used. None otherwise.
        system_alignment_score: Prompt vs system alignment [0,1] when available.
    """

    selected_model: str
    task_type: TaskType
    reason: str
    cost_estimate: float
    alternatives: list[str]
    classification_confidence: float
    complexity_tier: ComplexityTier | None = None
    system_alignment_score: float | None = None


class ModelRouter:
    """Intelligent model router. Selects the best model based on task, modality, cost, budget."""

    def __init__(
        self,
        profiles: list[ModelProfile],
        *,
        default_profile: str | None = None,
        routing_mode: RoutingMode = RoutingMode.AUTO,
        classifier: PromptClassifier | None = None,
        budget: Budget | None = None,
        budget_optimisation: bool = True,
        economy_at: float = 0.20,
        cheapest_at: float = 0.10,
        force_model: Model | None = None,
        routing_rule_callback: Callable[[str, TaskType, list[str]], str | None] | None = None,
    ) -> None:
        if not profiles and force_model is None:
            raise ValueError(
                "ModelRouter requires at least one profile when force_model is not set. "
                "Add profiles or set force_model to bypass routing."
            )
        if default_profile is not None:
            names = {p.name for p in profiles}
            if default_profile not in names:
                raise ValueError(
                    f"default_profile {default_profile!r} not in profile names: {sorted(names)}. "
                    "Set default_profile to a valid profile name or None."
                )
        self._profiles = list(profiles)
        self._default_profile = default_profile
        self._routing_mode = routing_mode
        self._classifier = classifier
        self._budget = budget
        self._prefer_cheap = budget_optimisation
        self._budget_low = economy_at
        self._budget_critical = cheapest_at
        self._force_model = force_model
        self._routing_rule_callback = routing_rule_callback
        self._modality_detector = ModalityDetector()

    def _get_classifier(self) -> PromptClassifier:
        if self._classifier is not None:
            return self._classifier
        return PromptClassifier()

    def _required_modalities(self, messages: list[Message] | None) -> set[Modality]:
        if not messages:
            return {Modality.TEXT}
        return self._modality_detector.detect(messages)

    def _filter_by_modality(
        self, profiles: list[ModelProfile], required: set[Modality]
    ) -> list[ModelProfile]:
        return [p for p in profiles if (p.modality_input or {Modality.TEXT}) >= required]

    def _filter_by_tools(
        self, profiles: list[ModelProfile], tools: list[ToolSpec] | None
    ) -> list[ModelProfile]:
        if not tools:
            return profiles
        return [p for p in profiles if p.supports_tools]

    def _filter_by_task(
        self, profiles: list[ModelProfile], task_type: TaskType
    ) -> list[ModelProfile]:
        return [p for p in profiles if task_type in p.strengths]

    def _budget_ratio(self) -> float | None:
        if self._budget is None or self._budget.run is None:
            return None
        remaining = self._budget.remaining
        limit = (self._budget.run or 0) - self._budget.reserve
        if limit <= 0:
            return None
        return remaining / limit if remaining is not None else None

    def _estimate_tokens(self, prompt: str, context: dict[str, object] | None) -> tuple[int, int]:
        in_tok: int | None = None
        if context:
            val = context.get("input_tokens_estimate")
            if isinstance(val, int):
                in_tok = val
        if in_tok is None:
            in_tok = count_tokens(prompt, "openai/gpt-4o")
        out_tok = 1024
        if context:
            val = context.get("max_output_tokens")
            if isinstance(val, int):
                out_tok = val
        return (in_tok, out_tok)

    def select_model(
        self,
        prompt: str,
        *,
        context: dict[str, object] | None = None,
    ) -> Model:
        """Select the best model for the given prompt. Simplified; use route() for full reason."""
        model, _task, _reason = self.route(prompt, context=context)
        return model

    def route(
        self,
        prompt: str,
        *,
        tools: list[ToolSpec] | None = None,
        context: dict[str, object] | None = None,
        messages: list[Message] | None = None,
        task_override: TaskType | None = None,
    ) -> tuple[Model, TaskType, RoutingReason]:
        """Full routing decision. Returns (model, task_type, routing_reason)."""
        if self._force_model is not None:
            in_tok, out_tok = self._estimate_tokens(prompt, context)
            cost = 0.0
            if hasattr(self._force_model, "estimate_cost"):
                cost = self._force_model.estimate_cost(in_tok, out_tok)
            return (
                self._force_model,
                task_override or TaskType.GENERAL,
                RoutingReason(
                    selected_model="force_model",
                    task_type=task_override or TaskType.GENERAL,
                    reason="Routing bypassed via force_model",
                    cost_estimate=cost,
                    alternatives=[],
                    classification_confidence=1.0,
                    complexity_tier=None,
                    system_alignment_score=None,
                ),
            )

        required_mod = self._required_modalities(messages)
        candidates = self._filter_by_modality(self._profiles, required_mod)
        candidates = self._filter_by_tools(candidates, tools)

        complexity_tier: ComplexityTier | None = None
        system_alignment_score: float | None = None
        if task_override is not None:
            task_type = task_override
            confidence = 1.0
        else:
            classifier = self._get_classifier()
            system_prompt: str | None = None
            if messages:
                for m in messages:
                    role = getattr(m, "role", None)
                    content = getattr(m, "content", None)
                    if role == "system" and isinstance(content, str) and content.strip():
                        system_prompt = content.strip()
                        break
            try:
                if hasattr(classifier, "classify_extended"):
                    ext = classifier.classify_extended(prompt, system_prompt)
                    task_type = ext.task_type
                    confidence = ext.confidence
                    complexity_tier = ext.complexity_tier
                    system_alignment_score = ext.system_alignment_score
                else:
                    task_type, confidence = classifier.classify(prompt)
            except Exception as e:
                logger.warning("Classification failed, using GENERAL: %s", e)
                task_type = classifier.low_confidence_fallback
                confidence = 0.0

        by_task = self._filter_by_task(candidates, task_type)
        if not by_task:
            names = [p.name for p in self._profiles]
            raise NoMatchingProfileError(
                f"No profile supports TaskType.{task_type.name} and modalities {required_mod}. "
                "Add a profile with matching strengths and modality_input.",
                required_task_type=task_type,
                required_modalities=required_mod,
                available_profiles=names,
            )

        profile_names = [p.name for p in by_task]
        if self._routing_rule_callback is not None:
            chosen = self._routing_rule_callback(prompt, task_type, profile_names)
            if chosen is not None:
                for p in by_task:
                    if p.name == chosen:
                        return self._make_result(
                            p,
                            by_task,
                            task_type,
                            confidence,
                            prompt,
                            context,
                            "Custom routing rule selected profile",
                            complexity_tier=complexity_tier,
                            system_alignment_score=system_alignment_score,
                        )
                logger.warning(
                    "Callback returned unknown profile %r; using default routing", chosen
                )

        in_tok, out_tok = self._estimate_tokens(prompt, context)
        ratio = self._budget_ratio()
        reason = ""

        if self._prefer_cheap and ratio is not None and ratio < self._budget_critical:
            by_task = sorted(by_task, key=lambda p: _estimate_cost_for_profile(p, in_tok, out_tok))
            selected = by_task[0]
            reason = "Budget critical; using cheapest capable model"
        elif self._prefer_cheap and ratio is not None and ratio < self._budget_low:
            by_task = sorted(by_task, key=lambda p: _estimate_cost_for_profile(p, in_tok, out_tok))
            selected = by_task[0]
            reason = "Budget low; preferring cheaper capable model"
        elif complexity_tier == ComplexityTier.HIGH:
            by_task = sorted(by_task, key=lambda p: -p.priority)
            selected = by_task[0]
            reason = f"Complexity HIGH; selected highest-priority ({selected.name})"
        elif self._routing_mode == RoutingMode.COST_FIRST:
            by_task = sorted(by_task, key=lambda p: _estimate_cost_for_profile(p, in_tok, out_tok))
            selected = by_task[0]
            reason = "COST_FIRST: selected cheapest capable model"
        elif self._routing_mode == RoutingMode.QUALITY_FIRST:
            by_task = sorted(by_task, key=lambda p: -p.priority)
            selected = by_task[0]
            reason = f"QUALITY_FIRST: selected highest-priority ({selected.name})"
        else:
            by_task = sorted(
                by_task,
                key=lambda p: (
                    -p.priority,
                    _estimate_cost_for_profile(p, in_tok, out_tok),
                ),
            )
            selected = by_task[0]
            reason = f"Model specializes in {task_type.value} tasks"

        return self._make_result(
            selected,
            by_task,
            task_type,
            confidence,
            prompt,
            context,
            reason,
            complexity_tier=complexity_tier,
            system_alignment_score=system_alignment_score,
        )

    def _make_result(
        self,
        selected: ModelProfile,
        candidates: list[ModelProfile],
        task_type: TaskType,
        confidence: float,
        prompt: str,
        context: dict[str, object] | None,
        reason: str,
        *,
        complexity_tier: ComplexityTier | None = None,
        system_alignment_score: float | None = None,
    ) -> tuple[Model, TaskType, RoutingReason]:
        in_tok, out_tok = self._estimate_tokens(prompt, context)
        cost = _estimate_cost_for_profile(selected, in_tok, out_tok)
        alternatives = [p.name for p in candidates if p.name != selected.name]
        return (
            selected.model,
            task_type,
            RoutingReason(
                selected_model=selected.name,
                task_type=task_type,
                reason=reason,
                cost_estimate=cost,
                alternatives=alternatives,
                classification_confidence=confidence,
                complexity_tier=complexity_tier,
                system_alignment_score=system_alignment_score,
            ),
        )
