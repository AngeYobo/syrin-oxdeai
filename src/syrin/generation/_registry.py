"""Provider registry for image and video generation.

Holds _IMAGE_PROVIDERS and _VIDEO_PROVIDERS so ImageGenerator/VideoGenerator
(config.py) can access them without circular imports.

Built-in names: gemini (Google image), dalle (OpenAI image), gemini (Google video).
"""

from __future__ import annotations

from typing import Any

from syrin.generation._gemini import GeminiImageProvider, GeminiVideoProvider
from syrin.generation._openai import DalleImageProvider
from syrin.generation._protocols import (
    ImageGenerationProvider,
    VideoGenerationProvider,
)

_IMAGE_PROVIDERS: dict[str, type[ImageGenerationProvider]] = {
    "gemini": GeminiImageProvider,
    "dalle": DalleImageProvider,
}
_VIDEO_PROVIDERS: dict[str, type[VideoGenerationProvider]] = {
    "gemini": GeminiVideoProvider,
}


def register_image_provider(name: str, cls: type[ImageGenerationProvider]) -> None:
    """Register an image generation provider. After registration, use ImageGenerator.Leonardo() etc."""
    _IMAGE_PROVIDERS[name.lower()] = cls


def register_video_provider(name: str, cls: type[VideoGenerationProvider]) -> None:
    """Register a video generation provider. After registration, use VideoGenerator.Leonardo() etc."""
    _VIDEO_PROVIDERS[name.lower()] = cls


def get_image_provider(
    name: str = "gemini",
    **kwargs: Any,
) -> ImageGenerationProvider:
    """Create an image provider instance by registered name."""
    cls = _IMAGE_PROVIDERS.get(name.lower())
    if cls is None:
        raise ValueError(
            f"Unknown image provider: {name!r}. Registered: {sorted(_IMAGE_PROVIDERS)}. "
            "Use register_image_provider() to add custom providers."
        )
    return cls(**kwargs)


def get_video_provider(
    name: str = "gemini",
    **kwargs: Any,
) -> VideoGenerationProvider:
    """Create a video provider instance by registered name."""
    cls = _VIDEO_PROVIDERS.get(name.lower())
    if cls is None:
        raise ValueError(
            f"Unknown video provider: {name!r}. Registered: {sorted(_VIDEO_PROVIDERS)}. "
            "Use register_video_provider() to add custom providers."
        )
    return cls(**kwargs)


def is_image_provider_registered(name: str) -> bool:
    """Return True if an image provider is registered under this name."""
    return name.lower() in _IMAGE_PROVIDERS


def is_video_provider_registered(name: str) -> bool:
    """Return True if a video provider is registered under this name."""
    return name.lower() in _VIDEO_PROVIDERS
