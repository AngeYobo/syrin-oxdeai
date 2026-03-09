"""ModalityDetector — detect media types present in messages. Returns set[Media]."""

from __future__ import annotations

from syrin.enums import Media
from syrin.types import Message

_PREFIX_LEN = 100


class ModalityDetector:
    """Detect media types present in message content. Used by ModelRouter to filter profiles.

    Returns set[Media]. TEXT is always included; IMAGE, VIDEO, AUDIO, FILE added when detected.
    Uses prefix-only checks for string content (avoids regex on large base64 payloads).
    Supports structured content (list of parts with type: image_url, image, video, etc.).
    """

    def detect(self, messages: list[Message]) -> set[Media]:
        """Return set of Media present in message content."""
        if not isinstance(messages, list):
            raise TypeError(
                f"ModalityDetector.detect requires list[Message]; got {type(messages).__name__}."
            )
        result: set[Media] = {Media.TEXT}
        for msg in messages:
            content = getattr(msg, "content", None) or ""
            if isinstance(content, list):
                self._detect_structured(content, result)
            elif isinstance(content, str):
                self._detect_string(content, result)
        return result

    def _detect_string(self, content: str, result: set[Media]) -> None:
        prefix = content[:_PREFIX_LEN]
        if "data:image" in prefix:
            result.add(Media.IMAGE)
        if "data:video" in prefix:
            result.add(Media.VIDEO)
        if "data:audio" in prefix:
            result.add(Media.AUDIO)
        if "data:application" in prefix:
            result.add(Media.FILE)
        if "file_url" in prefix or ('"type"' in prefix and "file" in prefix[:200]):
            result.add(Media.FILE)

    def _detect_structured(self, parts: list[object], result: set[Media]) -> None:
        for part in parts:
            if not isinstance(part, dict):
                continue
            t = part.get("type", "")
            if not isinstance(t, str):
                continue
            t_lower = t.lower()
            if t_lower in ("image_url", "image"):
                result.add(Media.IMAGE)
            elif t_lower == "video":
                result.add(Media.VIDEO)
            elif t_lower == "audio":
                result.add(Media.AUDIO)
            elif t_lower == "file":
                result.add(Media.FILE)
