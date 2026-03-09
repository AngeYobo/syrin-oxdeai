"""Cost-first routing with budget thresholds.

When budget is low, router prefers cheaper models. When critical, forces cheapest.
Uses Almock (no API key). Replace with real models for production.

Features: RoutingMode.COST_FIRST, economy_at, cheapest_at, budget_optimisation.

Run: python -m examples.17_routing.cost_first_budget_agent
Run with traces: python -m examples.17_routing.cost_first_budget_agent --trace
"""

from __future__ import annotations

import sys

from syrin import Agent, Budget
from syrin.model import Model
from syrin.router import (
    ModelProfile,
    ModelRouter,
    RouterConfig,
    RoutingMode,
    TaskType,
)


def main() -> None:
    # Cheap vs expensive (Almock; in production use gpt-4o-mini vs gpt-4o)
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
            strengths=[TaskType.GENERAL, TaskType.CODE, TaskType.REASONING],
            priority=100,
        ),
    ]
    router = ModelRouter(
        profiles=profiles,
        routing_mode=RoutingMode.COST_FIRST,
        budget_optimisation=True,
        economy_at=0.20,
        cheapest_at=0.10,
    )

    use_trace = "--trace" in sys.argv
    agent = Agent(
        model=[cheap, expensive],
        router_config=RouterConfig(router=router),
        system_prompt="You are helpful. Be concise.",
        budget=Budget(run=0.50),
        debug=use_trace,
    )

    # With full budget, COST_FIRST picks cheapest capable model
    r = agent.response("Say hi", task_type=TaskType.GENERAL)
    print(f"GENERAL (full budget) -> {r.routing_reason.selected_model}: {r.routing_reason.reason}")
    print(f"  cost_estimate=${r.routing_reason.cost_estimate:.6f}")

    # CODE: both capable; COST_FIRST picks cheap
    r = agent.response("Write one line of code", task_type=TaskType.CODE)
    print(f"CODE -> {r.routing_reason.selected_model}: {r.routing_reason.reason}")


if __name__ == "__main__":
    main()
