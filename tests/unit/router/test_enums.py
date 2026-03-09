"""Tests for router enums — TaskType, RoutingMode, ComplexityTier. Media lives in syrin.enums."""

from __future__ import annotations

from syrin.router import ComplexityTier, RoutingMode, TaskType


class TestComplexityTier:
    """Tests for ComplexityTier enum."""

    def test_all_values_present(self) -> None:
        expected = {"low", "medium", "high"}
        actual = {t.value for t in ComplexityTier}
        assert actual == expected

    def test_strenum_string_value(self) -> None:
        assert ComplexityTier.LOW == "low"
        assert ComplexityTier.MEDIUM == "medium"
        assert ComplexityTier.HIGH == "high"

    def test_from_string_compatible(self) -> None:
        assert ComplexityTier("low") is ComplexityTier.LOW
        assert ComplexityTier("high") is ComplexityTier.HIGH

    def test_members_count(self) -> None:
        assert len(ComplexityTier) == 3


class TestTaskType:
    """Tests for TaskType enum."""

    def test_all_values_present(self) -> None:
        expected = {
            "code",
            "general",
            "vision",
            "image_generation",
            "video",
            "video_generation",
            "planning",
            "reasoning",
            "creative",
            "translation",
        }
        actual = {t.value for t in TaskType}
        assert actual == expected

    def test_strenum_string_value(self) -> None:
        assert TaskType.CODE == "code"
        assert TaskType.GENERAL == "general"
        assert str(TaskType.VISION) == "vision"

    def test_from_string_compatible(self) -> None:
        assert TaskType("code") is TaskType.CODE
        assert TaskType("general") is TaskType.GENERAL

    def test_members_count(self) -> None:
        assert len(TaskType) == 10


class TestRoutingMode:
    """Tests for RoutingMode enum."""

    def test_all_values_present(self) -> None:
        expected = {"auto", "cost_first", "quality_first", "manual"}
        actual = {r.value for r in RoutingMode}
        assert actual == expected

    def test_strenum_string_value(self) -> None:
        assert RoutingMode.AUTO == "auto"
        assert RoutingMode.COST_FIRST == "cost_first"

    def test_from_string_compatible(self) -> None:
        assert RoutingMode("auto") is RoutingMode.AUTO
        assert RoutingMode("manual") is RoutingMode.MANUAL

    def test_members_count(self) -> None:
        assert len(RoutingMode) == 4
