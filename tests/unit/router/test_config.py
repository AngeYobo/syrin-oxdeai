"""Tests for RouterConfig — routing configuration."""

from __future__ import annotations

import pytest

from syrin.router import RoutingMode, TaskType
from syrin.router.config import RouterConfig


def _dummy_callback(prompt: str, task_type: TaskType, profiles: list[str]) -> str | None:
    return None


class TestRouterConfigValid:
    """Valid RouterConfig construction."""

    def test_minimal_config(self) -> None:
        cfg = RouterConfig()
        assert cfg.router is None
        assert cfg.classifier is None
        assert cfg.routing_mode == RoutingMode.AUTO
        assert cfg.force_model is None
        assert cfg.budget_optimisation is True
        assert cfg.economy_at == 0.20
        assert cfg.cheapest_at == 0.10
        assert cfg.max_cost_per_1k_tokens is None
        assert cfg.profiles is None
        assert cfg.routing_rule_callback is None

    def test_with_routing_mode(self) -> None:
        cfg = RouterConfig(routing_mode=RoutingMode.COST_FIRST)
        assert cfg.routing_mode == RoutingMode.COST_FIRST

    def test_with_budget_thresholds(self) -> None:
        cfg = RouterConfig(
            economy_at=0.25,
            cheapest_at=0.05,
        )
        assert cfg.economy_at == 0.25
        assert cfg.cheapest_at == 0.05

    def test_thresholds_at_boundary(self) -> None:
        cfg = RouterConfig(
            economy_at=0.5,
            cheapest_at=0.5,
        )
        assert cfg.economy_at == 0.5
        assert cfg.cheapest_at == 0.5

    def test_budget_optimisation_disabled(self) -> None:
        cfg = RouterConfig(budget_optimisation=False)
        assert cfg.budget_optimisation is False

    def test_max_cost_per_1k_tokens(self) -> None:
        cfg = RouterConfig(max_cost_per_1k_tokens=0.01)
        assert cfg.max_cost_per_1k_tokens == 0.01

    def test_routing_rule_callback(self) -> None:
        cfg = RouterConfig(routing_rule_callback=_dummy_callback)
        assert cfg.routing_rule_callback is _dummy_callback

    def test_with_explicit_router(self) -> None:
        from syrin.router import ModelRouter
        from syrin.router.defaults import DEFAULT_PROFILES

        profiles = list(DEFAULT_PROFILES.values())
        router = ModelRouter(profiles=profiles)
        cfg = RouterConfig(router=router)
        assert cfg.router is router

    def test_with_profiles(self) -> None:
        from syrin.model import Model
        from syrin.router import ModelProfile

        m = Model.Almock()
        p = ModelProfile(model=m, name="test", strengths=[TaskType.GENERAL])
        cfg = RouterConfig(profiles=[p])
        assert cfg.profiles == [p]

    def test_with_force_model(self) -> None:
        from syrin.model import Model

        m = Model.Almock()
        cfg = RouterConfig(force_model=m)
        assert cfg.force_model is m


class TestRouterConfigValidation:
    """RouterConfig validation."""

    def test_economy_at_out_of_range_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RouterConfig(economy_at=1.5)
        with pytest.raises(ValidationError):
            RouterConfig(economy_at=-0.1)

    def test_cheapest_at_out_of_range_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RouterConfig(cheapest_at=2.0)
        with pytest.raises(ValidationError):
            RouterConfig(cheapest_at=-0.01)

    def test_cheapest_gt_economy_raises(self) -> None:
        with pytest.raises(ValueError, match="cheapest_at.*<=.*economy_at"):
            RouterConfig(
                economy_at=0.10,
                cheapest_at=0.20,
            )
