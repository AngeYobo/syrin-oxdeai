"""Tools-aware routing — supports_tools excludes models without tool support.

When Agent has tools, only profiles with supports_tools=True are considered.
"""

from __future__ import annotations

from syrin import Agent, tool
from syrin.model import Model
from syrin.router import (
    ModelProfile,
    ModelRouter,
    RouterConfig,
    RoutingMode,
    TaskType,
)


@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: 72°F, sunny"


def main() -> None:
    text_only = Model.Almock(latency_min=0, latency_max=0)
    with_tools = Model.Almock(latency_min=0, latency_max=0)

    profiles = [
        ModelProfile(
            model=text_only,
            name="text-only",
            strengths=[TaskType.GENERAL],
            supports_tools=False,
            priority=90,
        ),
        ModelProfile(
            model=with_tools,
            name="with-tools",
            strengths=[TaskType.GENERAL],
            supports_tools=True,
            priority=80,
        ),
    ]
    router = ModelRouter(profiles=profiles, routing_mode=RoutingMode.AUTO)

    agent = Agent(
        model=[text_only, with_tools],
        router_config=RouterConfig(router=router),
        system_prompt="You are helpful.",
        tools=[get_weather],
    )

    # Agent has tools -> text-only excluded; routes to with-tools
    r = agent.response("What's the weather in NYC?")
    print(f"With tools -> {r.routing_reason.selected_model}")


if __name__ == "__main__":
    main()
