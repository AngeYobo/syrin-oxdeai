"""Tests for ModalityDetector — detect media types in messages (returns set[Media])."""

from __future__ import annotations

import pytest

from syrin.enums import Media, MessageRole
from syrin.router.modality import ModalityDetector
from syrin.types import Message


class TestModalityDetectorText:
    """Text-only messages."""

    def test_empty_messages_returns_text(self) -> None:
        detector = ModalityDetector()
        result = detector.detect([])
        assert result == {Media.TEXT}

    def test_plain_text_message(self) -> None:
        detector = ModalityDetector()
        msg = Message(role=MessageRole.USER, content="Hello world")
        result = detector.detect([msg])
        assert result == {Media.TEXT}

    def test_multiple_text_messages(self) -> None:
        detector = ModalityDetector()
        msgs = [
            Message(role=MessageRole.SYSTEM, content="You are helpful."),
            Message(role=MessageRole.USER, content="What is 2+2?"),
            Message(role=MessageRole.ASSISTANT, content="4"),
        ]
        result = detector.detect(msgs)
        assert result == {Media.TEXT}


class TestModalityDetectorImage:
    """Image detection via base64 or patterns in content."""

    def test_base64_image_data_url(self) -> None:
        detector = ModalityDetector()
        content = "Check this: data:image/png;base64,iVBORw0KGgo="
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.TEXT in result
        assert Media.IMAGE in result

    def test_base64_image_jpeg(self) -> None:
        detector = ModalityDetector()
        content = "Image: data:image/jpeg;base64,/9j/4AAQ="
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.IMAGE in result

    def test_base64_image_webp(self) -> None:
        detector = ModalityDetector()
        content = "data:image/webp;base64,UklGRg=="
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.IMAGE in result


class TestModalityDetectorVideo:
    """Video detection."""

    def test_base64_video(self) -> None:
        detector = ModalityDetector()
        content = "Video: data:video/mp4;base64,AAAA"
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.VIDEO in result
        assert Media.TEXT in result


class TestModalityDetectorAudio:
    """Audio detection."""

    def test_base64_audio(self) -> None:
        detector = ModalityDetector()
        content = "data:audio/mpeg;base64,//uQx"
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.AUDIO in result


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
        assert Media.TEXT in result
        assert Media.IMAGE in result

    def test_empty_content_messages(self) -> None:
        detector = ModalityDetector()
        msg = Message(role=MessageRole.ASSISTANT, content="")
        result = detector.detect([msg])
        assert result == {Media.TEXT}


class TestModalityDetectorFile:
    """FILE modality detection (PDF, file attachments)."""

    def test_base64_pdf(self) -> None:
        detector = ModalityDetector()
        content = "PDF doc: data:application/pdf;base64,JVBERi0xLjQK"
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.FILE in result
        assert Media.TEXT in result

    def test_base64_octet_stream(self) -> None:
        detector = ModalityDetector()
        content = "data:application/octet-stream;base64,SGVsbG8="
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.FILE in result

    def test_file_url_in_content(self) -> None:
        detector = ModalityDetector()
        content = '{"type":"file","file_url":{"url":"https://example.com/doc.pdf"}}'
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.FILE in result


class TestModalityDetectorValidation:
    """Input validation."""

    def test_non_list_raises(self) -> None:
        detector = ModalityDetector()
        with pytest.raises(TypeError):
            detector.detect("not a list")  # type: ignore[arg-type]


class TestModalityDetectorPrefixOnly:
    """Performance: only check content prefix, not full base64 payload."""

    def test_large_base64_only_checks_prefix(self) -> None:
        detector = ModalityDetector()
        payload = "A" * 6_000_000
        content = f"data:image/png;base64,{payload}"
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.IMAGE in result
        assert Media.TEXT in result

    def test_data_url_at_end_of_long_text_not_detected(self) -> None:
        detector = ModalityDetector()
        content = "x" * 200 + "data:image/png;base64,iVBORw0KGgo="
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.IMAGE not in result


class TestModalityDetectorStructuredContent:
    """Structured content (list of parts) — no regex on full base64."""

    def test_image_url_part(self) -> None:
        detector = ModalityDetector()
        content = [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
        ]
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.IMAGE in result
        assert Media.TEXT in result

    def test_image_part_inline(self) -> None:
        detector = ModalityDetector()
        content = [
            {"type": "text", "text": "Analyze"},
            {"type": "image", "image": {"data": "base64...", "mime_type": "image/png"}},
        ]
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.IMAGE in result

    def test_video_part(self) -> None:
        detector = ModalityDetector()
        content = [
            {"type": "text", "text": "Describe"},
            {"type": "video", "video": {"url": "https://example.com/vid.mp4"}},
        ]
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.VIDEO in result

    def test_file_part(self) -> None:
        detector = ModalityDetector()
        content = [
            {"type": "text", "text": "Extract text"},
            {"type": "file", "file": {"url": "https://example.com/doc.pdf"}},
        ]
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert Media.FILE in result

    def test_unknown_part_type_ignored(self) -> None:
        detector = ModalityDetector()
        content = [{"type": "unknown", "data": "x"}]
        msg = Message(role=MessageRole.USER, content=content)
        result = detector.detect([msg])
        assert result == {Media.TEXT}
