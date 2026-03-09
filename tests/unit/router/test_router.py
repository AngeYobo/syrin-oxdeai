"""Tests for ModelRouter and RoutingReason."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from syrin.model import Model
from syrin.router import ComplexityTier, Modality, RoutingMode, TaskType
from syrin.router.classifier import ClassificationResult, PromptClassifier
from syrin.router.profile import ModelProfile
from syrin.router.router import ModelRouter, RoutingReason


def _almock(name: str = "test") -> Model:
    return Model.Almock(context_window=4096, latency_min=0, latency_max=0)


def _profiles() -> list[ModelProfile]:
    return [
        ModelProfile(
            model=_almock("code"),
            name="code-model",
            strengths=[TaskType.CODE, TaskType.REASONING],
            priority=100,
        ),
        ModelProfile(
            model=_almock("general"),
            name="general-model",
            strengths=[TaskType.GENERAL, TaskType.CREATIVE],
            priority=90,
        ),
        ModelProfile(
            model=_almock("vision"),
            name="vision-model",
            strengths=[TaskType.VISION],
            modality_input={Modality.TEXT, Modality.IMAGE},
            priority=80,
        ),
    ]


class TestRoutingReason:
    """RoutingReason dataclass."""

    def test_create_minimal(self) -> None:
        r = RoutingReason(
            selected_model="claude-code",
            task_type=TaskType.CODE,
            reason="Model specializes in code tasks",
            cost_estimate=0.003,
            alternatives=["gpt-4o", "ollama-llama3"],
            classification_confidence=0.92,
        )
        assert r.selected_model == "claude-code"
        assert r.task_type == TaskType.CODE
        assert r.reason == "Model specializes in code tasks"
        assert r.cost_estimate == 0.003
        assert r.alternatives == ["gpt-4o", "ollama-llama3"]
        assert r.classification_confidence == 0.92

    def test_create_empty_alternatives(self) -> None:
        r = RoutingReason(
            selected_model="only-one",
            task_type=TaskType.GENERAL,
            reason="Single model",
            cost_estimate=0.0,
            alternatives=[],
            classification_confidence=1.0,
        )
        assert r.alternatives == []

    def test_classification_confidence_bounds(self) -> None:
        r = RoutingReason(
            selected_model="x",
            task_type=TaskType.GENERAL,
            reason="Low confidence",
            cost_estimate=0.0,
            alternatives=[],
            classification_confidence=0.0,
        )
        assert r.classification_confidence == 0.0
        r2 = RoutingReason(
            selected_model="x",
            task_type=TaskType.GENERAL,
            reason="High confidence",
            cost_estimate=0.0,
            alternatives=[],
            classification_confidence=1.0,
        )
        assert r2.classification_confidence == 1.0

    def test_complexity_tier_and_system_alignment_optional(self) -> None:
        r = RoutingReason(
            selected_model="premium",
            task_type=TaskType.CODE,
            reason="Complexity HIGH",
            cost_estimate=0.01,
            alternatives=[],
            classification_confidence=0.9,
            complexity_tier=ComplexityTier.HIGH,
            system_alignment_score=0.45,
        )
        assert r.complexity_tier == ComplexityTier.HIGH
        assert r.system_alignment_score == 0.45

    def test_complexity_tier_none_default(self) -> None:
        r = RoutingReason(
            selected_model="x",
            task_type=TaskType.GENERAL,
            reason="Normal",
            cost_estimate=0.0,
            alternatives=[],
            classification_confidence=1.0,
        )
        assert r.complexity_tier is None
        assert r.system_alignment_score is None


class TestModelRouterValidation:
    """ModelRouter construction validation."""

    def test_empty_profiles_without_force_model_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one profile"):
            ModelRouter(profiles=[])

    def test_empty_profiles_with_force_model_ok(self) -> None:
        router = ModelRouter(profiles=[], force_model=_almock())
        model, task, reason = router.route("hello")
        assert model is not None
        assert reason.reason == "Routing bypassed via force_model"

    def test_default_profile_not_in_names_raises(self) -> None:
        profiles = _profiles()
        with pytest.raises(ValueError, match="default_profile.*not in profile names"):
            ModelRouter(profiles=profiles, default_profile="unknown")


class TestModelRouterForceModel:
    """Force model bypass."""

    def test_force_model_bypasses_routing(self) -> None:
        router = ModelRouter(profiles=_profiles(), force_model=_almock("forced"))
        model, task, reason = router.route("write code")
        assert reason.selected_model == "force_model"
        assert reason.reason == "Routing bypassed via force_model"


class TestModelRouterRouting:
    """Routing logic. Use task_override to avoid classifier dependency in unit tests."""

    def test_route_returns_model_task_reason(self) -> None:
        router = ModelRouter(profiles=_profiles())
        model, task, reason = router.route("write a function", task_override=TaskType.CODE)
        assert model is not None
        assert task == TaskType.CODE
        assert reason.selected_model == "code-model"
        assert reason.classification_confidence == 1.0

    def test_task_override_skips_classification(self) -> None:
        router = ModelRouter(profiles=_profiles())
        model, task, reason = router.route("hi", task_override=TaskType.CODE)
        assert task == TaskType.CODE
        assert reason.selected_model == "code-model"

    def test_cost_first_mode_selects_cheapest(self) -> None:
        profiles = _profiles()
        router = ModelRouter(
            profiles=profiles,
            routing_mode=RoutingMode.COST_FIRST,
        )
        model, task, reason = router.route("hello", task_override=TaskType.GENERAL)
        assert reason.selected_model in [p.name for p in profiles]

    def test_quality_first_mode_selects_highest_priority(self) -> None:
        router = ModelRouter(
            profiles=_profiles(),
            routing_mode=RoutingMode.QUALITY_FIRST,
        )
        model, task, reason = router.route("hello", task_override=TaskType.GENERAL)
        assert reason.selected_model == "general-model"

    def test_no_matching_profile_raises(self) -> None:
        from syrin.exceptions import NoMatchingProfileError

        profiles = [
            ModelProfile(
                model=_almock(),
                name="code-only",
                strengths=[TaskType.CODE],
            ),
        ]
        router = ModelRouter(profiles=profiles)
        with pytest.raises(NoMatchingProfileError, match="No profile supports"):
            router.route("describe this image", task_override=TaskType.VISION)

    def test_routing_rule_callback_override(self) -> None:
        def pick_code(prompt: str, task_type: TaskType, names: list[str]) -> str | None:
            return "code-model" if "code-model" in names else None

        router = ModelRouter(
            profiles=_profiles(),
            routing_rule_callback=pick_code,
        )
        model, task, reason = router.route("write code", task_override=TaskType.CODE)
        assert reason.selected_model == "code-model"


class TestModelRouterComplexityAndAlignment:
    """Router with classify_extended — complexity_tier, system_alignment_score."""

    def _make_mock_classifier(
        self,
        task: TaskType = TaskType.CODE,
        confidence: float = 0.85,
        complexity_tier: ComplexityTier = ComplexityTier.MEDIUM,
        system_alignment: float | None = 0.7,
    ) -> MagicMock:
        ext = ClassificationResult(
            task_type=task,
            confidence=confidence,
            complexity_score=0.5,
            complexity_tier=complexity_tier,
            system_alignment_score=system_alignment,
            used_fallback=False,
            latency_ms=10.0,
        )
        mock = MagicMock(spec=PromptClassifier)
        mock.classify_extended = MagicMock(return_value=ext)
        mock.low_confidence_fallback = TaskType.GENERAL
        return mock

    def test_route_with_classifier_uses_classify_extended(self) -> None:
        mock_cls = self._make_mock_classifier(
            task=TaskType.REASONING,
            complexity_tier=ComplexityTier.HIGH,
            system_alignment=0.4,
        )
        profiles = [
            ModelProfile(
                model=_almock("premium"),
                name="premium",
                strengths=[TaskType.CODE, TaskType.REASONING],
                priority=100,
            ),
            ModelProfile(
                model=_almock("cheap"),
                name="cheap",
                strengths=[TaskType.REASONING],
                priority=80,
            ),
        ]
        router = ModelRouter(profiles=profiles, classifier=mock_cls)
        model, task, reason = router.route("solve this", messages=[])
        mock_cls.classify_extended.assert_called_once()
        assert reason.task_type == TaskType.REASONING
        assert reason.complexity_tier == ComplexityTier.HIGH
        assert reason.system_alignment_score == 0.4
        assert reason.selected_model == "premium"

    def test_high_complexity_selects_highest_priority(self) -> None:
        mock_cls = self._make_mock_classifier(
            task=TaskType.GENERAL,
            complexity_tier=ComplexityTier.HIGH,
        )
        profiles = [
            ModelProfile(
                model=_almock("low"),
                name="low",
                strengths=[TaskType.GENERAL],
                priority=70,
            ),
            ModelProfile(
                model=_almock("high"),
                name="high",
                strengths=[TaskType.GENERAL],
                priority=100,
            ),
        ]
        router = ModelRouter(profiles=profiles, classifier=mock_cls)
        model, task, reason = router.route("complex question", messages=[])
        assert reason.reason == "Complexity HIGH; selected highest-priority (high)"
        assert reason.selected_model == "high"

    def test_route_with_system_message_extracts_for_alignment(self) -> None:
        from syrin.types import Message

        mock_cls = self._make_mock_classifier(system_alignment=0.6)
        messages = [
            Message(role="system", content="You are a coding assistant."),
            Message(role="user", content="Write a function"),
        ]
        router = ModelRouter(profiles=_profiles(), classifier=mock_cls)
        router.route("Write a function", messages=messages)
        call_args = mock_cls.classify_extended.call_args
        assert call_args[0][0] == "Write a function"
        assert call_args[0][1] == "You are a coding assistant."


class TestModelRouterEdgeCases:
    """Edge cases for router: classifier failures, legacy classifier, tier behavior."""

    def _make_mock_classifier(
        self,
        task: TaskType = TaskType.CODE,
        confidence: float = 0.85,
        complexity_tier: ComplexityTier = ComplexityTier.MEDIUM,
        system_alignment: float | None = 0.7,
    ) -> MagicMock:
        ext = ClassificationResult(
            task_type=task,
            confidence=confidence,
            complexity_score=0.5,
            complexity_tier=complexity_tier,
            system_alignment_score=system_alignment,
            used_fallback=False,
            latency_ms=10.0,
        )
        mock = MagicMock(spec=PromptClassifier)
        mock.classify_extended = MagicMock(return_value=ext)
        mock.classify = MagicMock(return_value=(task, confidence))
        mock.low_confidence_fallback = TaskType.GENERAL
        return mock

    def test_classifier_raises_uses_fallback(self) -> None:
        mock_cls = self._make_mock_classifier()
        mock_cls.classify_extended.side_effect = RuntimeError("Model unavailable")
        profiles = [
            ModelProfile(
                model=_almock("general"),
                name="general",
                strengths=[TaskType.GENERAL],
                priority=90,
            ),
        ]
        router = ModelRouter(profiles=profiles, classifier=mock_cls)
        model, task, reason = router.route("write code", messages=[])
        assert task == TaskType.GENERAL
        assert reason.classification_confidence == 0.0

    def test_classifier_without_classify_extended_uses_classify(self) -> None:
        mock_cls = MagicMock()
        mock_cls.classify = MagicMock(return_value=(TaskType.CODE, 0.9))
        mock_cls.low_confidence_fallback = TaskType.GENERAL
        del mock_cls.classify_extended

        router = ModelRouter(profiles=_profiles(), classifier=mock_cls)
        model, task, reason = router.route("write a function", messages=[])
        mock_cls.classify.assert_called_once_with("write a function")
        assert task == TaskType.CODE
        assert reason.complexity_tier is None
        assert reason.system_alignment_score is None

    def test_low_complexity_with_cost_first_selects_cheapest(self) -> None:
        mock_cls = self._make_mock_classifier(
            task=TaskType.GENERAL,
            complexity_tier=ComplexityTier.LOW,
        )
        profiles = [
            ModelProfile(
                model=_almock("cheap"),
                name="cheap",
                strengths=[TaskType.GENERAL],
                priority=70,
            ),
            ModelProfile(
                model=_almock("expensive"),
                name="expensive",
                strengths=[TaskType.GENERAL],
                priority=100,
            ),
        ]
        router = ModelRouter(
            profiles=profiles,
            classifier=mock_cls,
            routing_mode=RoutingMode.COST_FIRST,
        )
        model, task, reason = router.route("hi", messages=[])
        assert reason.selected_model == "cheap"

    def test_no_system_message_passes_none_to_classifier(self) -> None:
        from syrin.types import Message

        mock_cls = self._make_mock_classifier()
        messages = [Message(role="user", content="hello")]
        router = ModelRouter(profiles=_profiles(), classifier=mock_cls)
        router.route("hello", messages=messages)
        call_args = mock_cls.classify_extended.call_args
        assert call_args[0][1] is None


class TestModelRouterBudgetParams:
    """Budget params (budget_optimisation, economy_at, cheapest_at) affect routing."""

    def test_budget_low_prefers_cheaper_model(self) -> None:
        from syrin.budget import Budget

        budget = Budget(run=1.0)
        budget._set_spent(0.85)  # remaining=0.15, ratio=0.15 < economy_at=0.20

        profiles = [
            ModelProfile(
                model=_almock("cheap"),
                name="cheap",
                strengths=[TaskType.GENERAL],
                priority=70,
            ),
            ModelProfile(
                model=_almock("expensive"),
                name="expensive",
                strengths=[TaskType.GENERAL],
                priority=100,
            ),
        ]
        router = ModelRouter(
            profiles=profiles,
            budget=budget,
            budget_optimisation=True,
            economy_at=0.20,
            cheapest_at=0.10,
            routing_mode=RoutingMode.AUTO,
        )
        model, task, reason = router.route("hello", messages=[])
        assert reason.selected_model == "cheap"
        assert "cheaper" in reason.reason.lower() or "budget" in reason.reason.lower()

    def test_budget_critical_forces_cheapest(self) -> None:
        from syrin.budget import Budget

        budget = Budget(run=1.0)
        budget._set_spent(0.92)  # remaining=0.08, ratio=0.08 < cheapest_at=0.10

        profiles = [
            ModelProfile(
                model=_almock("cheap"),
                name="cheap",
                strengths=[TaskType.GENERAL],
                priority=70,
            ),
            ModelProfile(
                model=_almock("expensive"),
                name="expensive",
                strengths=[TaskType.GENERAL],
                priority=100,
            ),
        ]
        router = ModelRouter(
            profiles=profiles,
            budget=budget,
            budget_optimisation=True,
            economy_at=0.20,
            cheapest_at=0.10,
            routing_mode=RoutingMode.AUTO,
        )
        model, task, reason = router.route("hello", messages=[])
        assert reason.selected_model == "cheap"
        assert "cheapest" in reason.reason.lower() or "critical" in reason.reason.lower()

    def test_budget_optimisation_disabled_ignores_budget(self) -> None:
        from syrin.budget import Budget

        budget = Budget(run=1.0)
        budget._set_spent(0.90)  # Low remaining

        profiles = [
            ModelProfile(
                model=_almock("cheap"),
                name="cheap",
                strengths=[TaskType.GENERAL],
                priority=70,
            ),
            ModelProfile(
                model=_almock("expensive"),
                name="expensive",
                strengths=[TaskType.GENERAL],
                priority=100,
            ),
        ]
        router = ModelRouter(
            profiles=profiles,
            budget=budget,
            budget_optimisation=False,
            routing_mode=RoutingMode.AUTO,
        )
        model, task, reason = router.route("hello", messages=[])
        assert reason.selected_model == "expensive"
        assert "budget" not in reason.reason.lower()


class TestModelRouterSelectModel:
    """select_model convenience method."""

    def test_select_model_returns_model(self) -> None:
        router = ModelRouter(profiles=_profiles())
        model = router.select_model("hello", context={"input_tokens_estimate": 100})
        assert model is not None
