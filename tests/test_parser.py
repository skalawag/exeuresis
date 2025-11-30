"""Tests for TEI XML parser."""

from pathlib import Path

import pytest

# We'll import this once we create it
# from exeuresis.parser import TEIParser


class TestTEIParser:
    """Test suite for TEI XML parsing functionality."""

    @pytest.fixture
    def sample_xml_path(self):
        """Path to minimal sample XML fixture."""
        return Path(__file__).parent / "fixtures" / "sample_minimal.xml"

    @pytest.fixture
    def euthyphro_xml_path(self):
        """Path to actual Euthyphro XML file."""
        return (
            Path(__file__).parent.parent
            / "canonical-greekLit"
            / "data"
            / "tlg0059"
            / "tlg001"
            / "tlg0059.tlg001.perseus-grc1.xml"
        )

    def test_parse_valid_xml(self, sample_xml_path):
        """Test 1: Should successfully parse a valid TEI XML file."""
        # This test will fail until we implement TEIParser
        from exeuresis.parser import TEIParser

        parser = TEIParser(sample_xml_path)
        assert parser is not None
        assert parser.tree is not None
        assert parser.root is not None

    def test_parse_validates_xml_structure(self, sample_xml_path):
        """Test that parser validates basic TEI structure."""
        from exeuresis.parser import TEIParser

        parser = TEIParser(sample_xml_path)
        # Should have TEI root element
        assert parser.root.tag == "{http://www.tei-c.org/ns/1.0}TEI"

    def test_parse_invalid_file_raises_error(self):
        """Test that parser raises error for non-existent file."""
        from exeuresis.parser import TEIParser

        with pytest.raises(FileNotFoundError):
            TEIParser(Path("/nonexistent/file.xml"))

    def test_extract_speakers(self, sample_xml_path):
        """Test 2: Should extract speaker names from header."""
        from exeuresis.parser import TEIParser

        parser = TEIParser(sample_xml_path)
        speakers = parser.get_speakers()

        assert len(speakers) == 2
        assert "Εὐθύφρων" in speakers
        assert "Σωκράτης" in speakers

    def test_extract_text_divisions(self, sample_xml_path):
        """Test 3: Should extract text divisions with their section numbers."""
        from exeuresis.parser import TEIParser

        parser = TEIParser(sample_xml_path)
        divisions = parser.get_divisions()

        assert len(divisions) >= 1
        # First division should be section 2
        assert divisions[0]["n"] == "2"
        assert divisions[0]["type"] == "textpart"
        assert divisions[0]["subtype"] == "section"

    def test_parse_missing_text_element_raises_error(self):
        """Test that parser raises InvalidTEIStructureError for missing <text> element."""
        from exeuresis.exceptions import InvalidTEIStructureError
        from exeuresis.parser import TEIParser

        invalid_xml = (
            Path(__file__).parent / "fixtures" / "invalid" / "missing_text_element.xml"
        )

        with pytest.raises(InvalidTEIStructureError) as exc_info:
            TEIParser(invalid_xml)

        assert "tei:text" in str(exc_info.value)
        assert str(invalid_xml) in str(exc_info.value)

    def test_parse_missing_body_element_raises_error(self):
        """Test that parser raises InvalidTEIStructureError for missing <body> element."""
        from exeuresis.exceptions import InvalidTEIStructureError
        from exeuresis.parser import TEIParser

        invalid_xml = (
            Path(__file__).parent / "fixtures" / "invalid" / "missing_body_element.xml"
        )

        with pytest.raises(InvalidTEIStructureError) as exc_info:
            TEIParser(invalid_xml)

        assert "tei:body" in str(exc_info.value)
        assert str(invalid_xml) in str(exc_info.value)
