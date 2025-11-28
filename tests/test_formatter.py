"""Tests for text formatting functionality."""

import pytest
from pathlib import Path

# from exeuresis.formatter import TextFormatter, OutputStyle


class TestTextFormatter:
    """Test suite for text formatting with various styles."""

    @pytest.fixture
    def sample_dialogue_data(self):
        """Sample dialogue data structure for testing."""
        return [
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "τί νεώτερον, ὦ Σώκρατες, γέγονεν;",
                "stephanus": ["2", "2a"],
            },
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "οὔτοι δὴ Ἀθηναῖοί γε, ὦ Εὐθύφρων, δίκην αὐτὴν καλοῦσιν ἀλλὰ γραφήν.",
                "stephanus": [],
            },
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "τί φῄς; γραφὴν σέ τις, ὡς ἔοικε, γέγραπται;",
                "stephanus": ["2b"],
            },
        ]

    def test_style_a_full_modern_edition(self, sample_dialogue_data):
        """Test 8: Style A should preserve all punctuation and apparatus."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter(sample_dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should include speaker labels
        assert "ΕΥΘ." in output
        assert "ΣΩ." in output

        # Should include Stephanus markers with new format
        # First section (2a) should show as [2], subsequent (2b) as [b]
        assert "[2]" in output  # First section of page 2
        assert "[b]" in output  # Second section (2b shows as just [b])

        # Should preserve punctuation
        assert ";" in output or ";" in output  # Greek question mark
        assert "," in output

        # Should have the Greek text
        assert "τί νεώτερον" in output
        assert "Ἀθηναῖοί" in output

    def test_style_a_paragraph_formatting(self, sample_dialogue_data):
        """Test 9: Style A should create readable paragraphs."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter(sample_dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should have line breaks between speakers
        lines = output.strip().split("\n")
        assert len(lines) >= 3  # At least 3 dialogue entries

    def test_style_d_scriptio_continua(self, sample_dialogue_data):
        """Test 10-12: Style D should produce uppercase continuous text."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter(sample_dialogue_data)
        output = formatter.format(OutputStyle.SCRIPTIO_CONTINUA)

        # Should be all uppercase
        assert output.isupper() or all(c.isupper() or not c.isalpha() for c in output)

        # Should not have punctuation
        assert "," not in output
        assert "." not in output
        assert ";" not in output
        assert "·" not in output

        # Should not have speaker labels
        assert "ΕΥΘ." not in output
        assert "ΣΩ." not in output

        # Should not have Stephanus markers
        assert "[" not in output
        assert "]" not in output
        assert "(" not in output
        assert ")" not in output

        # Should have the text in uppercase
        assert "ΝΕΩΤΕΡΟΝ" in output or "ΝΕΏΤΕΡΟΝ" in output

    def test_style_d_removes_word_boundaries(self, sample_dialogue_data):
        """Test 11: Style D should remove spaces between words."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter(sample_dialogue_data)
        output = formatter.format(OutputStyle.SCRIPTIO_CONTINUA)

        # Should be one continuous string (may have one newline at end)
        output_clean = output.strip()

        # Should not have multiple spaces
        assert "  " not in output_clean

        # For scriptio continua, we might want NO spaces at all
        # Let's check that it's mostly continuous
        # (allowing for potential single line breaks)
        words = output_clean.split()
        # Should be very few "words" if truly continuous
        # For now, let's just check it's much more compact than original
        assert len(words) <= 5  # Should be mostly one big string

    def test_format_empty_dialogue(self):
        """Test formatting with empty dialogue list."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter([])
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should return empty or minimal output
        assert len(output.strip()) == 0

    def test_format_with_missing_stephanus(self):
        """Test formatting dialogue entries that have no Stephanus markers."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        dialogue_data = [
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "οὔτοι δὴ Ἀθηναῖοί γε.",
                "stephanus": [],
            }
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should still format correctly
        assert "ΣΩ." in output
        assert "Ἀθηναῖοί" in output

    def test_integration_full_pipeline(self):
        """Test 22: End-to-end test with actual Euthyphro XML."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor
        from exeuresis.formatter import TextFormatter, OutputStyle

        euthyphro_path = (
            Path(__file__).parent.parent
            / "canonical-greekLit"
            / "data"
            / "tlg0059"
            / "tlg001"
            / "tlg0059.tlg001.perseus-grc1.xml"
        )

        if not euthyphro_path.exists():
            pytest.skip("Euthyphro XML file not found")

        # Full pipeline
        parser = TEIParser(euthyphro_path)
        extractor = TextExtractor(parser)
        dialogue = extractor.get_dialogue_text()
        formatter = TextFormatter(dialogue)

        # Test Style A
        output_a = formatter.format(OutputStyle.FULL_MODERN)
        assert len(output_a) > 1000  # Should be substantial
        assert "ΕΥΘ." in output_a
        assert "ΣΩ." in output_a

        # Test Style D
        output_d = formatter.format(OutputStyle.SCRIPTIO_CONTINUA)
        assert len(output_d) > 1000
        assert output_d.isupper() or all(
            c.isupper() or not c.isalpha() for c in output_d
        )
        assert "ΕΥΘ." not in output_d  # No labels in scriptio continua

    def test_style_b_minimal_punctuation(self, sample_dialogue_data):
        """Test Style B: Minimal punctuation (periods and question marks only)."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter(sample_dialogue_data)
        output = formatter.format(OutputStyle.MINIMAL_PUNCTUATION)

        # Should include question marks
        assert ";" in output  # Greek question mark

        # Should include speaker labels
        assert "ΕΥΘ." in output
        assert "ΣΩ." in output

    def test_style_c_no_punctuation(self, sample_dialogue_data):
        """Test Style C: No punctuation but preserves labels and spacing."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter(sample_dialogue_data)
        output = formatter.format(OutputStyle.NO_PUNCTUATION)

        # Should have speaker labels
        assert "ΕΥΘ." in output or "ΣΩ." in output

        # Should not have commas (removed)
        assert "," not in output

    def test_style_e_scriptio_continua(self, sample_dialogue_data):
        """Test Style E: Ancient scriptio continua format."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter(sample_dialogue_data)
        output = formatter.format(OutputStyle.SCRIPTIO_CONTINUA)

        # Should be uppercase
        assert output.isupper() or output.strip().isupper()

        # Should not have speaker labels
        assert "ΕΥΘ." not in output
        assert "ΣΩ." not in output

    def test_style_s_stephanus_layout(self, sample_dialogue_data):
        """Test Style S: Stephanus 1578 edition layout."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter(sample_dialogue_data)
        output = formatter.format(OutputStyle.STEPHANUS_LAYOUT)

        # Should have output
        assert len(output) > 0

        # Stephanus markers should appear
        assert "2" in output or "[" in output

    def test_all_styles_produce_output(self, sample_dialogue_data):
        """Test that all output styles produce valid output."""
        from exeuresis.formatter import TextFormatter, OutputStyle

        formatter = TextFormatter(sample_dialogue_data)

        # Test all implemented styles (skip CUSTOM as it's not implemented)
        for style in OutputStyle:
            if style == OutputStyle.CUSTOM:
                continue
            output = formatter.format(style)
            assert len(output) > 0, f"Style {style} produced empty output"
