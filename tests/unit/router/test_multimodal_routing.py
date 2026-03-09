"""TDD tests for multi-modal routing — IMAGE_GENERATION, VIDEO_GENERATION, keyword fallback."""

from __future__ import annotations

from unittest.mock import patch

from syrin.router import TaskType
from syrin.router.classifier import PromptClassifier, _keyword_detect_generation


class TestKeywordDetectGeneration:
    """Keyword-based generation detection — works without sentence-transformers."""

    def test_generate_image_variants(self) -> None:
        """Valid: common phrases for image generation."""
        for prompt in [
            "Generate an image of a rat",
            "generate a picture of a sunset",
            "create an image of a cat",
            "draw me a dog",
            "make an image of mountains",
            "Create a photo of the ocean",
        ]:
            result = _keyword_detect_generation(prompt)
            assert result is not None
            task, conf = result
            assert task == TaskType.IMAGE_GENERATION
            assert conf >= 0.80

    def test_generate_video_variants(self) -> None:
        """Valid: common phrases for video generation."""
        for prompt in [
            "Generate a video of a walking person",
            "create a video of ocean waves",
            "make a short clip",
        ]:
            result = _keyword_detect_generation(prompt)
            assert result is not None
            task, conf = result
            assert task == TaskType.VIDEO_GENERATION
            assert conf >= 0.80

    def test_no_match_general_prompts(self) -> None:
        """Invalid: general prompts should not match generation."""
        for prompt in [
            "hello",
            "what is the weather",
            "describe this image",
            "summarize this video",
            "write a function",
        ]:
            result = _keyword_detect_generation(prompt)
            assert result is None

    def test_no_match_vision_analysis(self) -> None:
        """Vision (understand image) is not image generation."""
        for prompt in [
            "what is in this picture",
            "describe the image",
            "extract text from image",
        ]:
            result = _keyword_detect_generation(prompt)
            assert result is None or result[0] != TaskType.IMAGE_GENERATION

    def test_empty_whitespace_returns_none(self) -> None:
        assert _keyword_detect_generation("") is None
        assert _keyword_detect_generation("   ") is None

    def test_edge_case_case_insensitive(self) -> None:
        result = _keyword_detect_generation("GENERATE AN IMAGE OF A RAT")
        assert result is not None
        assert result[0] == TaskType.IMAGE_GENERATION


class TestPromptClassifierImageGeneration:
    """PromptClassifier classifies image generation with or without embeddings."""

    def test_classify_image_generation_via_keyword(self) -> None:
        """Keyword path detects image gen before embeddings (no sentence-transformers needed)."""
        c = PromptClassifier(use_keyword_fallback=True)
        task, conf = c.classify("Generate an image of a rat")
        assert task == TaskType.IMAGE_GENERATION
        assert conf >= 0.80

    def test_classify_video_generation_via_keyword(self) -> None:
        c = PromptClassifier(use_keyword_fallback=True)
        task, conf = c.classify("create a video of waves")
        assert task == TaskType.VIDEO_GENERATION
        assert conf >= 0.80

    def test_classify_fallback_to_general_when_no_keyword_match_and_no_embeddings(
        self,
    ) -> None:
        """When no keyword match and embeddings fail, use low_confidence_fallback (no raise)."""
        with patch(
            "syrin.router.classifier._load_sentence_transformers",
            side_effect=ImportError("No module named 'sentence_transformers'"),
        ):
            c = PromptClassifier(
                use_keyword_fallback=True, low_confidence_fallback=TaskType.GENERAL
            )
            task, conf = c.classify("hello how are you")
            assert task == TaskType.GENERAL
            assert conf == 0.0


class TestRouterImageGenerationRouting:
    """ModelRouter routes IMAGE_GENERATION to profiles with output_media IMAGE."""

    def test_route_image_generation_selects_vision_profile(self) -> None:
        from syrin.enums import Media
        from syrin.model import Model
        from syrin.router import ModelRouter
        from syrin.router.enums import RoutingMode

        general = Model.OpenAI(
            "gpt-4o-mini",
            profile_name="general",
            strengths=[TaskType.GENERAL],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
            priority=80,
        )
        vision = Model.OpenAI(
            "gpt-4o",
            profile_name="vision",
            strengths=[TaskType.VISION, TaskType.IMAGE_GENERATION],
            input_media={Media.TEXT, Media.IMAGE},
            output_media={Media.TEXT, Media.IMAGE, Media.VIDEO},
            priority=90,
        )
        router = ModelRouter(models=[general, vision], routing_mode=RoutingMode.AUTO)
        model, task, reason = router.route(
            "Generate an image of a rat", task_override=TaskType.IMAGE_GENERATION
        )
        assert task == TaskType.IMAGE_GENERATION
        assert model is vision
        assert "vision" in reason.selected_model.lower() or reason.selected_model == "vision"

    def test_route_generate_image_prompt_routes_to_vision_via_keyword_classification(self) -> None:
        """Without task_override: keyword classifier detects IMAGE_GENERATION, router picks vision."""
        from syrin.enums import Media
        from syrin.model import Model
        from syrin.router import ModelRouter, PromptClassifier
        from syrin.router.enums import RoutingMode

        general = Model.OpenAI(
            "gpt-4o-mini",
            profile_name="general",
            strengths=[TaskType.GENERAL],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
            priority=80,
        )
        vision = Model.OpenAI(
            "gpt-4o",
            profile_name="vision",
            strengths=[TaskType.VISION, TaskType.IMAGE_GENERATION],
            input_media={Media.TEXT, Media.IMAGE},
            output_media={Media.TEXT, Media.IMAGE, Media.VIDEO},
            priority=90,
        )
        classifier = PromptClassifier(use_keyword_fallback=True)
        router = ModelRouter(
            models=[general, vision],
            routing_mode=RoutingMode.AUTO,
            classifier=classifier,
        )
        model, task, reason = router.route("Generate an image of a rat")
        assert task == TaskType.IMAGE_GENERATION
        assert reason.selected_model == "vision"
        assert model is vision
