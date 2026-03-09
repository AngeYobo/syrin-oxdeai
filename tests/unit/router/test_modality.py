"""Tests for ModalityDetector — detect modalities in messages."""

from __future__ import annotations

import pytest

from syrin.enums import MessageRole
from syrin.router import Modality
from syrin.router.modality import ModalityDetector
from syrin.types import Message


class TestModalityDetectorText:
    """Text-only messages."""

    def test_empty_messages_returns_text(self) -> None:
        detector = ModalityDetector()
        result = detector.detect([])
        assert result == {Modality.TEXT}

    def test_plain_text_message(self) -> None:
        detector = ModalityDetector()
        msg = Message(role=MessageRole.USER, content="Hello world")
        result = detector.detect([msg])
        assert result == {Modality.TEXT}

    def test_multiple_text_messages(self) -> None:
        detector = ModalityDetector()
        msgs = [
            Message(role=MessageRole.SYSTEM, content="You are helpful."),
            Message(role=MessageRole.USER, content="What is 2+2?"),
            Message(role=MessageRole.ASSISTANT, content="4"),
        ]
        result = detector.detect(msgs)
        assert result == {Modality.TEXT}


class TestModalityDetectorImage:
    """Image detection via base64 or patterns in content."""

    def test_base64_image_data_url(self) -> None:
        detector = ModalityDetector()
        content = "Check this: data:image/png;base64,iVBORw0KGgo="
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Modality.TEXT in result
        assert Modality.IMAGE in result

    def test_base64_image_jpeg(self) -> None:
        detector = ModalityDetector()
        content = "Image: data:image/jpeg;base64,/9j/4AAQ="
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Modality.IMAGE in result

    def test_base64_image_webp(self) -> None:
        detector = ModalityDetector()
        content = "data:image/webp;base64,UklGRg=="
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Modality.IMAGE in result


class TestModalityDetectorVideo:
    """Video detection."""

    def test_base64_video(self) -> None:
        detector = ModalityDetector()
        content = "Video: data:video/mp4;base64,AAAA"
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Modality.VIDEO in result
        assert Modality.TEXT in result


class TestModalityDetectorAudio:
    """Audio detection."""

    def test_base64_audio(self) -> None:
        detector = ModalityDetector()
        content = "data:audio/mpeg;base64,//uQx"
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Modality.AUDIO in result


class TestModalityDetectorCombined:
    """Multiple modalities in one or more messages."""

    def test_text_and_image(self) -> None:
        detector = ModalityDetector()
        msgs = [
            Message(role=MessageRole.USER, content="Describe this image"),
            Message(
                role=MessageRole.USER,
                content="data:image/png;base64,iVBORw0KGgo=",
            ),
        ]
        result = detector.detect(msgs)
        assert Modality.TEXT in result
        assert Modality.IMAGE in result

    def test_empty_content_messages(self) -> None:
        detector = ModalityDetector()
        msg = Message(role=MessageRole.ASSISTANT, content="")
        result = detector.detect([msg])
        assert result == {Modality.TEXT}


class TestModalityDetectorValidation:
    """Input validation."""

    def test_non_list_raises(self) -> None:
        detector = ModalityDetector()
        with pytest.raises((TypeError, ValueError)):
            detector.detect("not a list")  # type: ignore[arg-type]
