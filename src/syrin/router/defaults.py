"""Default model profiles for routing. Use or override when building ModelRouter."""

from __future__ import annotations

from syrin.model import Model
from syrin.router.enums import Modality, TaskType
from syrin.router.profile import ModelProfile

# Default profiles. Models use api_key=None; pass keys when instantiating Agent or override.
# Developers can use these as-is or replace with their own Model instances.
DEFAULT_PROFILES: dict[str, ModelProfile] = {
    "claude-code": ModelProfile(
        model=Model.Anthropic("claude-sonnet-4-5", api_key=None),
        name="claude-code",
        strengths=[TaskType.CODE, TaskType.REASONING, TaskType.PLANNING],
        modality_input={Modality.TEXT},
        modality_output={Modality.TEXT},
        priority=100,
    ),
    "gpt-general": ModelProfile(
        model=Model.OpenAI("gpt-4o", api_key=None),
        name="gpt-general",
        strengths=[TaskType.GENERAL, TaskType.CREATIVE, TaskType.TRANSLATION],
        modality_input={Modality.TEXT},
        modality_output={Modality.TEXT},
        priority=90,
    ),
    "gemini-vision": ModelProfile(
        model=Model.Google("gemini-2.0-flash", api_key=None),
        name="gemini-vision",
        strengths=[TaskType.VISION, TaskType.VIDEO],
        modality_input={Modality.TEXT, Modality.IMAGE, Modality.VIDEO},
        modality_output={Modality.TEXT, Modality.IMAGE},
        priority=80,
    ),
}
