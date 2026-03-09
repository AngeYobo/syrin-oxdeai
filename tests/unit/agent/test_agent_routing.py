"""Tests for Agent routing integration."""

from __future__ import annotations

import pytest

from syrin import Agent
from syrin.model import Model
from syrin.router import RouterConfig, RoutingMode, TaskType
from syrin.router.agent_integration import build_router_from_models, profiles_from_models
from syrin.router.profile import ModelProfile


def _almock(name: str = "test") -> Model:
    return Model.Almock(context_window=4096, latency_min=0, latency_max=0)


class TestProfilesFromModels:
    """profiles_from_models helper."""

    def test_empty_list_returns_empty(self) -> None:
        assert profiles_from_models([]) == []

    def test_single_model_creates_one_profile(self) -> None:
        m = _almock("a")
        profiles = profiles_from_models([m])
        assert len(profiles) == 1
        assert profiles[0].model is m
        assert profiles[0].name in ("almock", "test")
        assert TaskType.GENERAL in profiles[0].strengths

    def test_multiple_models_creates_unique_names(self) -> None:
        profiles = profiles_from_models([_almock(), _almock(), _almock()])
        names = [p.name for p in profiles]
        assert len(set(names)) == 3

    def test_custom_strengths(self) -> None:
        m = _almock()
        profiles = profiles_from_models([m], strengths=[TaskType.CODE, TaskType.REASONING])
        assert profiles[0].strengths == [TaskType.CODE, TaskType.REASONING]


class TestBuildRouterFromModels:
    """build_router_from_models helper."""

    def test_build_without_config(self) -> None:
        models = [_almock("a"), _almock("b")]
        router = build_router_from_models(models)
        assert router is not None
        assert len(router._profiles) == 2

    def test_build_with_router_config_uses_explicit_router(self) -> None:
        explicit = build_router_from_models([_almock()])
        cfg = RouterConfig(router=explicit)
        router = build_router_from_models([_almock(), _almock()], router_config=cfg)
        assert router is explicit

    def test_build_with_router_config_force_model(self) -> None:
        forced = _almock("forced")
        cfg = RouterConfig(force_model=forced)
        router = build_router_from_models([_almock()], router_config=cfg)
        model, _, reason = router.route("hello")
        assert model is forced
        assert reason.reason == "Routing bypassed via force_model"


class TestAgentModelList:
    """Agent with model list."""

    def test_single_model_list_no_routing(self) -> None:
        agent = Agent(model=[Model.Almock()], system_prompt="Hi")
        assert agent._router is None
        r = agent.response("hello")
        assert r.content
        assert r.model

    def test_model_list_with_router_config(self) -> None:
        agent = Agent(
            model=[Model.Almock(), Model.Almock(latency_min=0, latency_max=0)],
            router_config=RouterConfig(routing_mode=RoutingMode.COST_FIRST),
            system_prompt="Hi",
        )
        assert agent._router is not None
        r = agent.response("hello")
        assert r.content
        assert r.model

    def test_empty_model_list_raises(self) -> None:
        with pytest.raises(TypeError, match="cannot be empty"):
            Agent(model=[], system_prompt="Hi")

    def test_invalid_model_in_list_raises(self) -> None:
        with pytest.raises(TypeError, match=r"model\[0\] must be Model"):
            Agent(model=["not-a-model"], system_prompt="Hi")


class TestAgentTaskOverride:
    """Agent task_type override in response/arun."""

    def test_task_override_passed_to_router(self) -> None:
        from syrin.router.router import ModelRouter

        code_m = Model.Almock()
        general_m = Model.Almock()
        profiles = [
            ModelProfile(
                model=code_m,
                name="code",
                strengths=[TaskType.CODE],
            ),
            ModelProfile(
                model=general_m,
                name="general",
                strengths=[TaskType.GENERAL],
            ),
        ]
        router = ModelRouter(profiles=profiles)
        agent = Agent(
            model=[code_m, general_m],
            router_config=RouterConfig(router=router),
            system_prompt="Hi",
        )
        r = agent.response("hello", task_type=TaskType.CODE)
        assert r.content
        assert r.task_type == TaskType.CODE
        assert r.routing_reason is not None
        assert r.routing_reason.selected_model == "code"


class TestAgentResponseRoutingMetadata:
    """Response routing metadata."""

    def test_response_has_routing_reason_when_routing(self) -> None:
        agent = Agent(
            model=[Model.Almock(), Model.Almock()],
            router_config=RouterConfig(routing_mode=RoutingMode.COST_FIRST),
            system_prompt="Hi",
        )
        r = agent.response("hello")
        assert r.routing_reason is not None
        assert r.routing_reason.task_type is not None
        assert r.model_used is not None
