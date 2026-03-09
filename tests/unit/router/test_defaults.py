"""Tests for DEFAULT_PROFILES — default model profiles."""

from __future__ import annotations

from syrin.router import Modality, TaskType
from syrin.router.defaults import DEFAULT_PROFILES


class TestDefaultProfiles:
    """DEFAULT_PROFILES structure and content."""

    def test_has_expected_keys(self) -> None:
        assert "claude-code" in DEFAULT_PROFILES
        assert "gpt-general" in DEFAULT_PROFILES
        assert "gemini-vision" in DEFAULT_PROFILES

    def test_claude_code_strengths(self) -> None:
        p = DEFAULT_PROFILES["claude-code"]
        assert TaskType.CODE in p.strengths
        assert TaskType.REASONING in p.strengths
        assert TaskType.PLANNING in p.strengths
        assert p.modality_input == {Modality.TEXT}
        assert p.priority == 100

    def test_gpt_general_strengths(self) -> None:
        p = DEFAULT_PROFILES["gpt-general"]
        assert TaskType.GENERAL in p.strengths
        assert TaskType.CREATIVE in p.strengths
        assert TaskType.TRANSLATION in p.strengths
        assert p.priority == 90

    def test_gemini_vision_strengths_and_modality(self) -> None:
        p = DEFAULT_PROFILES["gemini-vision"]
        assert TaskType.VISION in p.strengths
        assert TaskType.VIDEO in p.strengths
        assert Modality.IMAGE in p.modality_input
        assert Modality.VIDEO in p.modality_input
        assert Modality.TEXT in p.modality_input
        assert p.priority == 80

    def test_all_profiles_have_model(self) -> None:
        for name, profile in DEFAULT_PROFILES.items():
            assert profile.model is not None
            assert profile.name == name
