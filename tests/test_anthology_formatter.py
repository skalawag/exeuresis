"""Tests for anthology formatter."""

import pytest

from exeuresis.anthology_extractor import AnthologyBlock
from exeuresis.anthology_formatter import AnthologyFormatter
from exeuresis.exceptions import InvalidStyleError
from exeuresis.formatter import OutputStyle


class TestAnthologyFormatter:
    """Tests for AnthologyFormatter class."""

    def test_format_single_block_style_a(self):
        """Test formatting single block with style A."""
        block = AnthologyBlock(
            work_title_en="Euthyphro",
            work_title_gr="Εὐθύφρων",
            range_display="5a",
            segments=[
                {
                    "speaker": "Εὐθύφρων",
                    "label": "ΕΥΘ.",
                    "text": "Sample text",
                    "stephanus": ["5a"],
                }
            ],
            book=None,
        )

        formatter = AnthologyFormatter(style=OutputStyle.FULL_MODERN)
        output = formatter.format_blocks([block])

        # Should contain header
        assert "Euthyphro (Εὐθύφρων) 5a" in output
        assert "-" * 79 in output
        # Should contain text
        assert "Sample text" in output

    def test_format_multiple_blocks(self):
        """Test formatting multiple blocks with blank line separation."""
        block1 = AnthologyBlock(
            work_title_en="Euthyphro",
            work_title_gr="Εὐθύφρων",
            range_display="5a",
            segments=[
                {"speaker": "", "label": "", "text": "Text 1", "stephanus": ["5a"]}
            ],
        )
        block2 = AnthologyBlock(
            work_title_en="Republic",
            work_title_gr="Πολιτεία",
            range_display="354b",
            segments=[
                {"speaker": "", "label": "", "text": "Text 2", "stephanus": ["354b"]}
            ],
            book="1",
        )

        formatter = AnthologyFormatter(style=OutputStyle.FULL_MODERN)
        output = formatter.format_blocks([block1, block2])

        # Should contain both headers
        assert "Euthyphro (Εὐθύφρων) 5a" in output
        assert "Republic (Πολιτεία) 1.354b" in output

        # Should have blank line between blocks
        lines = output.split("\n")
        # Find the blank line separator
        blank_lines = [i for i, line in enumerate(lines) if line == ""]
        assert len(blank_lines) > 0

    def test_format_with_style_b(self):
        """Test formatting with style B (minimal punctuation)."""
        block = AnthologyBlock(
            work_title_en="Euthyphro",
            work_title_gr="Εὐθύφρων",
            range_display="5a",
            segments=[
                {"speaker": "", "label": "", "text": "Text", "stephanus": ["5a"]}
            ],
        )

        formatter = AnthologyFormatter(style=OutputStyle.MINIMAL_PUNCTUATION)
        output = formatter.format_blocks([block])

        assert "Euthyphro (Εὐθύφρων) 5a" in output

    def test_format_style_e_raises_error(self):
        """Test that style E raises InvalidStyleError."""
        block = AnthologyBlock(
            work_title_en="Euthyphro",
            work_title_gr="Εὐθύφρων",
            range_display="5a",
            segments=[
                {"speaker": "", "label": "", "text": "Text", "stephanus": ["5a"]}
            ],
        )

        with pytest.raises(InvalidStyleError, match="Style E .* not supported"):
            formatter = AnthologyFormatter(style=OutputStyle.SCRIPTIO_CONTINUA)

    def test_format_style_s_raises_error(self):
        """Test that style S raises InvalidStyleError."""
        block = AnthologyBlock(
            work_title_en="Euthyphro",
            work_title_gr="Εὐθύφρων",
            range_display="5a",
            segments=[
                {"speaker": "", "label": "", "text": "Text", "stephanus": ["5a"]}
            ],
        )

        with pytest.raises(InvalidStyleError, match="Style S .* not supported"):
            formatter = AnthologyFormatter(style=OutputStyle.STEPHANUS_LAYOUT)

    def test_format_empty_blocks_list(self):
        """Test formatting empty blocks list."""
        formatter = AnthologyFormatter(style=OutputStyle.FULL_MODERN)
        output = formatter.format_blocks([])
        assert output == ""
