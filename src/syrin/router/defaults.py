"""Default model profiles for routing. Use or override when building ModelRouter."""

from __future__ import annotations

from syrin.enums import Media
from syrin.model import Model
from syrin.router.enums import TaskType


def get_default_profiles() -> dict[str, Model]:
    """Return default models with routing metadata. Lazy — models created on demand.

    Keys are profile names. Values are Model instances with strengths, input_media,
    output_media, priority set. Use: ModelRouter(models=list(get_default_profiles().values())).
    """
    return {
        "claude-code": Model.Anthropic(
            "claude-sonnet-4-5",
            api_key=None,
            profile_name="claude-code",
            strengths=[TaskType.CODE, TaskType.REASONING, TaskType.PLANNING],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
            priority=100,
        ),
        "gpt-general": Model.OpenAI(
            "gpt-4o",
            api_key=None,
            profile_name="gpt-general",
            strengths=[TaskType.GENERAL, TaskType.CREATIVE, TaskType.TRANSLATION],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
            priority=90,
        ),
        "gemini-vision": Model.Google(
            "gemini-2.0-flash",
            api_key=None,
            profile_name="gemini-vision",
            strengths=[TaskType.VISION, TaskType.VIDEO],
            input_media={Media.TEXT, Media.IMAGE, Media.VIDEO},
            output_media={Media.TEXT, Media.IMAGE},
            priority=80,
        ),
    }
