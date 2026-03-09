"""QUALITY_FIRST routing — always pick highest-priority capable model.

Use when cost is secondary; prefer best model for the task.
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
    premium = Model.Almock(pricing_tier="high", latency_min=0, latency_max=0)

    profiles = [
        ModelProfile(
            model=cheap,
            name="cheap",
            strengths=[TaskType.GENERAL, TaskType.CODE],
            priority=80,
        ),
        ModelProfile(
            model=premium,
            name="premium",
            strengths=[TaskType.GENERAL, TaskType.CODE, TaskType.REASONING],
            priority=100,
        ),
    ]
    router = ModelRouter(
        profiles=profiles,
        routing_mode=RoutingMode.QUALITY_FIRST,
    )

    agent = Agent(
        model=[cheap, premium],
        router_config=RouterConfig(router=router),
        system_prompt="You are helpful.",
    )

    # QUALITY_FIRST picks premium (higher priority) when both support task
    r = agent.response("Hello", task_type=TaskType.GENERAL)
    print(f"GENERAL -> {r.routing_reason.selected_model}: {r.routing_reason.reason}")

    r = agent.response("Solve 2+2", task_type=TaskType.REASONING)
    print(f"REASONING -> {r.routing_reason.selected_model}: {r.routing_reason.reason}")


if __name__ == "__main__":
    main()
