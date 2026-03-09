"""Tests for get_default_profiles — default model profiles."""

from __future__ import annotations

from syrin.enums import Media
from syrin.router import TaskType
from syrin.router.defaults import get_default_profiles


class TestDefaultProfiles:
    """get_default_profiles() structure and content."""

    def test_has_expected_keys(self) -> None:
        profiles = get_default_profiles()
        assert "claude-code" in profiles
        assert "gpt-general" in profiles
        assert "gemini-vision" in profiles

    def test_claude_code_strengths(self) -> None:
        profiles = get_default_profiles()
        p = profiles["claude-code"]
        assert TaskType.CODE in p.strengths
        assert TaskType.REASONING in p.strengths
        assert TaskType.PLANNING in p.strengths
        assert p.input_media == {Media.TEXT}
        assert p.priority == 100

    def test_gpt_general_strengths(self) -> None:
        profiles = get_default_profiles()
        p = profiles["gpt-general"]
        assert TaskType.GENERAL in p.strengths
        assert TaskType.CREATIVE in p.strengths
        assert TaskType.TRANSLATION in p.strengths
        assert p.priority == 90

    def test_gemini_vision_strengths_and_modality(self) -> None:
        profiles = get_default_profiles()
        p = profiles["gemini-vision"]
        assert TaskType.VISION in p.strengths
        assert TaskType.VIDEO in p.strengths
        assert Media.IMAGE in p.input_media
        assert Media.VIDEO in p.input_media
        assert Media.TEXT in p.input_media
        assert p.priority == 80

    def test_all_profiles_have_model(self) -> None:
        profiles = get_default_profiles()
        for name, model in profiles.items():
            assert model is not None
            assert model.profile_name == name
