"""Vision/modality routing — ModalityDetector routes image prompts to vision models.

When messages contain images (base64 data URLs), router picks profiles with
modality_input including IMAGE. Text-only profiles excluded.
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
    # Almock (no real vision; for structure demo)
    text_model = Model.Almock(latency_min=0, latency_max=0)
    vision_model = Model.Almock(latency_min=0, latency_max=0)

    profiles = [
        ModelProfile(
            model=text_model,
            name="text-only",
            strengths=[TaskType.GENERAL, TaskType.CODE],
            modality_input={Modality.TEXT},
            modality_output={Modality.TEXT},
            priority=90,
        ),
        ModelProfile(
            model=vision_model,
            name="vision",
            strengths=[TaskType.VISION, TaskType.GENERAL],
            modality_input={Modality.TEXT, Modality.IMAGE},
            modality_output={Modality.TEXT},
            priority=85,
        ),
    ]
    router = ModelRouter(profiles=profiles, routing_mode=RoutingMode.AUTO)

    agent = Agent(
        model=[text_model, vision_model],
        router_config=RouterConfig(router=router),
        system_prompt="You are helpful.",
    )

    # Text prompt -> text-only (higher priority for GENERAL)
    r = agent.response("Describe this", task_type=TaskType.GENERAL)
    print(f"Text prompt -> {r.routing_reason.selected_model}")

    # Vision task -> vision profile (only vision supports VISION)
    r2 = agent.response("What's in this image?", task_type=TaskType.VISION)
    print(f"Vision task -> {r2.routing_reason.selected_model}")


if __name__ == "__main__":
    main()
