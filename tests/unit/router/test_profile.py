"""Tests for ModelProfile — model capability profile for routing."""

from __future__ import annotations

import pytest

from syrin.model import Model
from syrin.router import Modality, TaskType
from syrin.router.profile import ModelProfile


def _almock(name: str) -> Model:
    """Create an Almock model for tests."""
    return Model.Almock(
        context_window=4096,
        latency_min=0,
        latency_max=0,
    )


class TestModelProfileValid:
    """Valid ModelProfile construction and attributes."""

    def test_minimal_profile(self) -> None:
        model = _almock("test")
        profile = ModelProfile(
            model=model,
            name="code-model",
            strengths=[TaskType.CODE],
        )
        assert profile.model is model
        assert profile.name == "code-model"
        assert profile.strengths == [TaskType.CODE]
        assert profile.modality_input == {Modality.TEXT}
        assert profile.modality_output == {Modality.TEXT}
        assert profile.supports_tools is True
        assert profile.priority == 100

    def test_full_profile(self) -> None:
        model = _almock("vision")
        profile = ModelProfile(
            model=model,
            name="vision-model",
            strengths=[TaskType.VISION, TaskType.VIDEO],
            modality_input={Modality.TEXT, Modality.IMAGE},
            modality_output={Modality.TEXT},
            supports_tools=False,
            priority=80,
        )
        assert profile.name == "vision-model"
        assert TaskType.VISION in profile.strengths
        assert TaskType.VIDEO in profile.strengths
        assert Modality.IMAGE in profile.modality_input
        assert profile.supports_tools is False
        assert profile.priority == 80

    def test_default_modality(self) -> None:
        profile = ModelProfile(
            model=_almock("x"),
            name="x",
            strengths=[TaskType.GENERAL],
        )
        assert profile.modality_input == {Modality.TEXT}
        assert profile.modality_output == {Modality.TEXT}

    def test_priority_zero_allowed(self) -> None:
        profile = ModelProfile(
            model=_almock("x"),
            name="x",
            strengths=[TaskType.GENERAL],
            priority=0,
        )
        assert profile.priority == 0


class TestModelProfileValidation:
    """ModelProfile construction validation."""

    def test_empty_strengths_raises(self) -> None:
        with pytest.raises(ValueError, match="strengths.*non-empty"):
            ModelProfile(
                model=_almock("x"),
                name="x",
                strengths=[],
            )

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="name.*non-empty"):
            ModelProfile(
                model=_almock("x"),
                name="",
                strengths=[TaskType.GENERAL],
            )

    def test_whitespace_only_name_raises(self) -> None:
        with pytest.raises(ValueError, match="name.*non-empty"):
            ModelProfile(
                model=_almock("x"),
                name="   ",
                strengths=[TaskType.GENERAL],
            )

    def test_negative_priority_raises(self) -> None:
        with pytest.raises(ValueError, match="priority.*>= 0"):
            ModelProfile(
                model=_almock("x"),
                name="x",
                strengths=[TaskType.GENERAL],
                priority=-1,
            )
