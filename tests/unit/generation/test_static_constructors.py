"""Tests for ImageGenerator and VideoGenerator static constructors and provider registry."""

from __future__ import annotations

import pytest

from syrin.generation import ImageGenerator, VideoGenerator, register_image_provider
from syrin.generation._result import GenerationResult


class TestImageGeneratorStaticConstructors:
    """ImageGenerator.Gemini() and ImageGenerator.<Registered>()."""

    def test_gemini_static_constructor(self) -> None:
        """ImageGenerator.Gemini(api_key=...) returns ImageGenerator with Gemini provider."""
        gen = ImageGenerator.Gemini(api_key="test-key")
        assert gen.image_model == "imagen-4.0-generate-001"
        assert gen.provider is not None

    def test_from_provider_gemini(self) -> None:
        """ImageGenerator.from_provider('gemini', ...) works."""
        gen = ImageGenerator.from_provider("gemini", api_key="x")
        assert gen.image_model == "imagen-4.0-generate-001"

    def test_registered_provider_static_namespace(self) -> None:
        """After register_image_provider, ImageGenerator.Leonardo() works."""

        class MockProvider:
            def __init__(self, api_key=None, **kw):
                pass

            def generate(
                self,
                prompt,
                *,
                aspect_ratio="1:1",
                number_of_images=1,
                output_mime_type="image/png",
                model=None,
                **kw,
            ):
                return [GenerationResult(success=True, url="mock://leonardo")]

        register_image_provider("leonardo", MockProvider)
        try:
            gen = ImageGenerator.Leonardo(api_key="x")
            assert gen.image_model == "default"
            results = gen.generate("test")
            assert results[0].url == "mock://leonardo"
        finally:
            from syrin.generation._registry import _IMAGE_PROVIDERS

            _IMAGE_PROVIDERS.pop("leonardo", None)

    def test_unregistered_provider_raises_attribute_error(self) -> None:
        """ImageGenerator.Flex() when Flex not registered raises AttributeError."""
        with pytest.raises(AttributeError, match="Flex"):
            ImageGenerator.Flex(api_key="x")  # type: ignore[attr-defined]

    def test_dalle_static_constructor(self) -> None:
        """ImageGenerator.DALLE(api_key=...) returns generator with dall-e-3 model."""
        gen = ImageGenerator.DALLE(api_key="sk-fake")
        assert gen.image_model == "dall-e-3"


class TestVideoGeneratorStaticConstructors:
    """VideoGenerator.Gemini() and VideoGenerator.<Registered>()."""

    def test_gemini_static_constructor(self) -> None:
        """VideoGenerator.Gemini(api_key=...) returns VideoGenerator with Gemini provider."""
        gen = VideoGenerator.Gemini(api_key="test-key")
        assert gen.video_model == "veo-2.0-generate-001"
        assert gen.provider is not None

    def test_from_provider_gemini(self) -> None:
        """VideoGenerator.from_provider('gemini', ...) works."""
        gen = VideoGenerator.from_provider("gemini", api_key="x")
        assert gen.video_model == "veo-2.0-generate-001"

    def test_unregistered_provider_raises_attribute_error(self) -> None:
        """VideoGenerator.Flex() when Flex not registered raises AttributeError."""
        with pytest.raises(AttributeError, match="Flex"):
            VideoGenerator.Flex(api_key="x")  # type: ignore[attr-defined]
