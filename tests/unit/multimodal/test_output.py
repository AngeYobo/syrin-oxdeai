"""Tests for multimodal output handling (MediaAttachment, Response.attachments)."""

from __future__ import annotations

from syrin.response import MediaAttachment, Response


class TestMediaAttachment:
    """Tests for MediaAttachment dataclass."""

    def test_media_attachment_with_content_bytes(self) -> None:
        """MediaAttachment with content_bytes and content_type."""
        att = MediaAttachment(
            type="image",
            content_bytes=b"\x89PNG\r\n\x1a\n",
            content_type="image/png",
        )
        assert att.type == "image"
        assert att.content_bytes == b"\x89PNG\r\n\x1a\n"
        assert att.url is None
        assert att.content_type == "image/png"

    def test_media_attachment_with_url(self) -> None:
        """MediaAttachment with url and content_type."""
        att = MediaAttachment(
            type="image",
            url="https://example.com/image.png",
            content_type="image/png",
        )
        assert att.type == "image"
        assert att.content_bytes is None
        assert att.url == "https://example.com/image.png"
        assert att.content_type == "image/png"

    def test_media_attachment_video(self) -> None:
        """MediaAttachment with type video."""
        att = MediaAttachment(
            type="video",
            url="https://example.com/video.mp4",
            content_type="video/mp4",
        )
        assert att.type == "video"

    def test_media_attachment_audio(self) -> None:
        """MediaAttachment with type audio."""
        att = MediaAttachment(
            type="audio",
            content_bytes=b"RIFF....",
            content_type="audio/wav",
        )
        assert att.type == "audio"


class TestResponseAttachments:
    """Tests for Response.attachments."""

    def test_response_attachments_default_empty(self) -> None:
        """Response has empty attachments by default."""
        r = Response(content="Hello")
        assert r.attachments == []

    def test_response_attachments_with_attachment(self) -> None:
        """Response can carry MediaAttachment list."""
        att = MediaAttachment(
            type="image",
            content_bytes=b"data",
            content_type="image/png",
        )
        r = Response(
            content="Here is the image.",
            attachments=[att],
        )
        assert len(r.attachments) == 1
        assert r.attachments[0].type == "image"
        assert r.attachments[0].content_bytes == b"data"

    def test_response_attachments_multiple(self) -> None:
        """Response can carry multiple attachments."""
        att1 = MediaAttachment(type="image", url="u1", content_type="image/png")
        att2 = MediaAttachment(type="audio", url="u2", content_type="audio/mpeg")
        r = Response(
            content="Done",
            attachments=[att1, att2],
        )
        assert len(r.attachments) == 2
        assert r.attachments[0].url == "u1"
        assert r.attachments[1].url == "u2"
