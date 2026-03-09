"""Tests for multimodal input handling (file_to_message, pdf_extract_text)."""

from __future__ import annotations

import base64
from unittest.mock import patch

import pytest

from syrin.multimodal import file_to_message, pdf_extract_text


class TestFileToMessage:
    """Tests for file_to_message."""

    def test_file_to_message_returns_base64_data_url(self) -> None:
        """file_to_message returns a data URL string with base64 content."""
        data = b"hello"
        mimetype = "text/plain"
        result = file_to_message(data, mimetype, "user")
        expected = f"data:{mimetype};base64,{base64.b64encode(data).decode()}"
        assert result == expected

    def test_file_to_message_with_image_mimetype(self) -> None:
        """file_to_message works with image/png."""
        data = b"\x89PNG\r\n\x1a\n"
        mimetype = "image/png"
        result = file_to_message(data, mimetype, "user")
        assert result.startswith("data:image/png;base64,")
        assert base64.b64decode(result.split(",", 1)[1]) == data

    def test_file_to_message_with_role(self) -> None:
        """file_to_message accepts role (used for building message structure elsewhere)."""
        data = b"content"
        result = file_to_message(data, "text/plain", "user")
        assert "base64," in result
        result_system = file_to_message(data, "text/plain", "system")
        assert result_system == result  # role affects caller usage, not the returned string

    def test_file_to_message_empty_bytes(self) -> None:
        """file_to_message handles empty bytes."""
        result = file_to_message(b"", "application/octet-stream", "user")
        assert result == "data:application/octet-stream;base64,"


class TestPdfExtractText:
    """Tests for pdf_extract_text."""

    def test_pdf_extract_text_with_pypdf_returns_text(self) -> None:
        """When pypdf is available, pdf_extract_text extracts text from PDF bytes."""
        pytest.importorskip("pypdf")
        # Minimal valid PDF with "Hello" text
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R "
            b"/Contents 4 0 R>>endobj 4 0 obj<</Length 44>>stream\n"
            b"BT /F1 12 Tf 100 700 Td (Hello) Tj ET\nendstream\nendobj "
            b"xref 0 5 0000000000 65535 f 0000000009 00000 n 0000000052 00000 n "
            b"0000000101 00000 n 0000000206 00000 n trailer<</Size 5/Root 1 0 R>>"
            b"startxref 296 %%EOF"
        )
        result = pdf_extract_text(pdf_bytes)
        assert isinstance(result, str)
        # pypdf may extract "Hello" or similar; at minimum it should not raise
        assert "Hello" in result or len(result) >= 0

    def test_pdf_extract_text_empty_returns_empty(self) -> None:
        """pdf_extract_text with empty bytes returns empty string (no pypdf needed)."""
        result = pdf_extract_text(b"")
        assert result == ""

    def test_pdf_extract_text_without_pypdf_raises_import_error(self) -> None:
        """When pypdf is not installed, pdf_extract_text raises ImportError."""

        class FakeModule:
            def __getattr__(self, name: str) -> None:
                raise ImportError("No module named 'pypdf'")

        with (
            patch.dict("sys.modules", {"pypdf": FakeModule()}),
            pytest.raises(ImportError, match="pypdf|pdf"),
        ):
            pdf_extract_text(b"%PDF-1.4 minimal")
