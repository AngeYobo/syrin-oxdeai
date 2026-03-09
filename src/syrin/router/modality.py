"""ModalityDetector — detect modalities present in messages."""

from __future__ import annotations

import re

from syrin.router.enums import Modality
from syrin.types import Message

# Patterns for detecting modalities in message content (str)
_BASE64_IMAGE = re.compile(
    r"data:image/[a-zA-Z0-9+.+-]+;base64,[A-Za-z0-9+/=]+",
    re.IGNORECASE,
)
_BASE64_VIDEO = re.compile(
    r"data:video/[a-zA-Z0-9+.+-]+;base64,[A-Za-z0-9+/=]+",
    re.IGNORECASE,
)
_BASE64_AUDIO = re.compile(
    r"data:audio/[a-zA-Z0-9+.+-]+;base64,[A-Za-z0-9+/=]+",
    re.IGNORECASE,
)


class ModalityDetector:
    """Detect modalities present in message content. Used by ModelRouter to filter profiles.

    Inspects message content for base64 data URLs (image, video, audio).
    TEXT is always included. IMAGE, VIDEO, AUDIO are added when detected.
    """

    def detect(self, messages: list[Message]) -> set[Modality]:
        """Return set of modalities present in message content.

        Args:
            messages: List of Message objects.

        Returns:
            Set of Modality (always includes TEXT; adds IMAGE, VIDEO, AUDIO as present).
        """
        if not isinstance(messages, list):
            raise TypeError(
                f"ModalityDetector.detect requires list[Message]; got {type(messages).__name__}."
            )
        result: set[Modality] = {Modality.TEXT}
        for msg in messages:
            content = getattr(msg, "content", None) or ""
            if not isinstance(content, str):
                continue
            if _BASE64_IMAGE.search(content):
                result.add(Modality.IMAGE)
            if _BASE64_VIDEO.search(content):
                result.add(Modality.VIDEO)
            if _BASE64_AUDIO.search(content):
                result.add(Modality.AUDIO)
        return result
