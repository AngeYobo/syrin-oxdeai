"""Use DEFAULT_PROFILES — built-in claude-code, gpt-general, gemini-vision.

Pass API keys when creating Agent (keys injected into profiles).
Uses Almock here so it runs without keys; swap to real models for production.
"""

from __future__ import annotations

from syrin import Agent
from syrin.model import Model
from syrin.router import (
    Modality,
    ModelProfile,
    ModelRouter,
    RouterConfig,
    RoutingMode,
    TaskType,
)


def main() -> None:
    # Mirror DEFAULT_PROFILES structure with Almock (no keys)
    m = Model.Almock(latency_min=0, latency_max=0)
    profiles = [
        ModelProfile(
            model=m,
            name="claude-code",
            strengths=[TaskType.CODE, TaskType.REASONING, TaskType.PLANNING],
            priority=100,
        ),
        ModelProfile(
            model=m,
            name="gpt-general",
            strengths=[TaskType.GENERAL, TaskType.CREATIVE, TaskType.TRANSLATION],
            priority=90,
        ),
        ModelProfile(
            model=m,
            name="gemini-vision",
            strengths=[TaskType.VISION, TaskType.VIDEO],
            modality_input={Modality.TEXT, Modality.IMAGE},
            modality_output={Modality.TEXT},
            priority=80,
        ),
    ]

    # To use real DEFAULT_PROFILES: profiles = list(DEFAULT_PROFILES.values())
    # and pass API keys to Model.Anthropic/OpenAI/Google when creating models.

    router = ModelRouter(profiles=profiles, routing_mode=RoutingMode.AUTO)
    agent = Agent(
        model=[m, m, m],
        router_config=RouterConfig(router=router),
        system_prompt="You are helpful.",
    )

    r = agent.response("write a python function", task_type=TaskType.CODE)
    print(f"CODE -> {r.routing_reason.selected_model}")

    r = agent.response("hello", task_type=TaskType.GENERAL)
    print(f"GENERAL -> {r.routing_reason.selected_model}")


if __name__ == "__main__":
    main()
