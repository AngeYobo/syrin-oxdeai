"""Cost comparison — COST_FIRST picks cheapest capable model.

Compare cost_estimate across profiles. Use for cost-sensitive routing.
"""

from __future__ import annotations

from syrin import Agent
from syrin.model import Model
from syrin.router import (
    ModelProfile,
    ModelRouter,
    RouterConfig,
    RoutingMode,
    TaskType,
)


def main() -> None:
    cheap = Model.Almock(pricing_tier="low", latency_min=0, latency_max=0)
    expensive = Model.Almock(pricing_tier="high", latency_min=0, latency_max=0)

    profiles = [
        ModelProfile(
            model=cheap,
            name="cheap",
            strengths=[TaskType.GENERAL, TaskType.CODE],
            priority=80,
        ),
        ModelProfile(
            model=expensive,
            name="expensive",
            strengths=[TaskType.GENERAL, TaskType.CODE],
            priority=100,
        ),
    ]
    router = ModelRouter(
        profiles=profiles,
        routing_mode=RoutingMode.COST_FIRST,
    )

    agent = Agent(
        model=[cheap, expensive],
        router_config=RouterConfig(router=router),
        system_prompt="You are helpful.",
    )

    r = agent.response("hi", task_type=TaskType.GENERAL)
    print(
        f"Routed to: {r.routing_reason.selected_model} | cost_estimate=${r.routing_reason.cost_estimate:.6f}"
    )
