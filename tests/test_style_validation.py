"""Tests for output style validation."""

from pathlib import Path

import pytest

from exeuresis.exceptions import InvalidStyleError
from exeuresis.extractor import TextExtractor
from exeuresis.formatter import OutputStyle, TextFormatter
from exeuresis.parser import TEIParser


class TestStyleValidation:
    """Test suite for validating style usage constraints."""

    @pytest.fixture
    def plato_euthyphro_path(self):
        """Path to Plato's Euthyphro (tlg0059)."""
        return (
            Path(__file__).parent.parent
            / "canonical-greekLit"
            / "data"
            / "tlg0059"
            / "tlg001"
            / "tlg0059.tlg001.perseus-grc1.xml"
        )

    @pytest.fixture
    def thucydides_path(self):
        """Path to Thucydides' History (tlg0003) - not Plato."""
        return (
            Path(__file__).parent.parent
            / "canonical-greekLit"
            / "data"
            / "tlg0003"
            / "tlg001"
            / "tlg0003.tlg001.perseus-grc2.xml"
        )

    def test_style_s_works_with_plato(self, plato_euthyphro_path):
        """Test that Style S (Stephanus layout) works with Plato's works."""
        if not plato_euthyphro_path.exists():
            pytest.skip("Euthyphro XML file not found")

        parser = TEIParser(plato_euthyphro_path)
        extractor = TextExtractor(parser)
        dialogue = extractor.get_dialogue_text()

        # Should not raise an error for Plato
        formatter = TextFormatter(dialogue, extractor=extractor, parser=parser)
        output = formatter.format(OutputStyle.STEPHANUS_LAYOUT)

        assert len(output) > 0

    def test_style_s_fails_with_non_plato(self, thucydides_path):
        """Test that Style S (Stephanus layout) raises error for non-Platonic works."""
        if not thucydides_path.exists():
            pytest.skip("Thucydides XML file not found")

        parser = TEIParser(thucydides_path)
        extractor = TextExtractor(parser)
        dialogue = extractor.get_dialogue_text()

        formatter = TextFormatter(dialogue, extractor=extractor, parser=parser)

        # Should raise InvalidStyleError for Thucydides
        with pytest.raises(InvalidStyleError) as exc_info:
            formatter.format(OutputStyle.STEPHANUS_LAYOUT)

        # Check error message
        assert "tlg0059" in str(exc_info.value)
        assert "Plato" in str(exc_info.value)
        assert "Stephanus" in str(exc_info.value)

    def test_parser_extracts_author_id_plato(self, plato_euthyphro_path):
        """Test that parser correctly extracts Plato's author ID."""
        if not plato_euthyphro_path.exists():
            pytest.skip("Euthyphro XML file not found")

        parser = TEIParser(plato_euthyphro_path)
        author_id = parser.get_author_id()

        assert author_id == "tlg0059"

    def test_parser_extracts_author_id_thucydides(self, thucydides_path):
        """Test that parser correctly extracts Thucydides' author ID."""
        if not thucydides_path.exists():
            pytest.skip("Thucydides XML file not found")

        parser = TEIParser(thucydides_path)
        author_id = parser.get_author_id()

        assert author_id == "tlg0003"

    def test_other_styles_work_with_non_plato(self, thucydides_path):
        """Test that other styles (A-E) work fine with non-Platonic works."""
        if not thucydides_path.exists():
            pytest.skip("Thucydides XML file not found")

        parser = TEIParser(thucydides_path)
        extractor = TextExtractor(parser)
        dialogue = extractor.get_dialogue_text()

        formatter = TextFormatter(dialogue, extractor=extractor, parser=parser)

        # Test that styles A-E work without error
        for style in [
            OutputStyle.FULL_MODERN,
            OutputStyle.MINIMAL_PUNCTUATION,
            OutputStyle.NO_PUNCTUATION,
            OutputStyle.NO_PUNCTUATION_NO_LABELS,
            OutputStyle.SCRIPTIO_CONTINUA,
        ]:
            output = formatter.format(style)
            assert len(output) > 0, f"Style {style} produced empty output"
