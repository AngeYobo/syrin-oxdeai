"""ModelRouter — intelligent model selection by task type.

Uses task_override to demonstrate routing without requiring classifier-embeddings.
"""

import os

from syrin.model import Model
from syrin.router import (
    ModelProfile,
    ModelRouter,
    RoutingMode,
    TaskType,
)


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "sk-demo")
    profiles = [
        ModelProfile(
            model=Model.OpenAI("gpt-4o-mini", api_key=api_key),
            name="general",
            strengths=[TaskType.GENERAL, TaskType.CREATIVE],
            priority=90,
        ),
        ModelProfile(
            model=Model.OpenAI("gpt-4o", api_key=api_key),
            name="code",
            strengths=[TaskType.CODE, TaskType.REASONING],
            priority=100,
        ),
    ]

    router = ModelRouter(
        profiles=profiles,
        routing_mode=RoutingMode.AUTO,
    )

    # Use task_override to select by task without classifier
    for prompt, task in [
        ("write a sorting function", TaskType.CODE),
        ("hello, how are you?", TaskType.GENERAL),
    ]:
        model, task_type, reason = router.route(prompt, task_override=task)
        print(f"  {prompt!r}")
        print(f"    -> {reason.selected_model} | {reason.reason}")
        print(f"    cost_estimate=${reason.cost_estimate:.6f}")


if __name__ == "__main__":
    main()
