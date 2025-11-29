"""Tests for text extraction functionality."""

from pathlib import Path
import textwrap

import pytest

# from exeuresis.extractor import TextExtractor
# from exeuresis.parser import TEIParser


class TestTextExtractor:
    """Test suite for text extraction from parsed TEI XML."""

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

    @pytest.fixture
    def plutarch_xml_path(self):
        """Path to actual Plutarch De animae procreatione XML file."""
        return (
            Path(__file__).parent.parent
            / "canonical-greekLit"
            / "data"
            / "tlg0007"
            / "tlg134"
            / "tlg0007.tlg134.perseus-grc2.xml"
        )

    @pytest.fixture
    def sample_sections_path(self):
        """Path to sample section-based XML fixture (Isocrates-style)."""
        return Path(__file__).parent / "fixtures" / "sample_sections.xml"

    @pytest.fixture
    def trapeziticus_xml_path(self):
        """Path to actual Isocrates Trapeziticus XML file."""
        return (
            Path(__file__).parent.parent
            / "canonical-greekLit"
            / "data"
            / "tlg0010"
            / "tlg005"
            / "tlg0010.tlg005.perseus-grc2.xml"
        )

    def test_extract_dialogue_text(self, sample_xml_path):
        """Test 4: Should extract text from <said> elements."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        parser = TEIParser(sample_xml_path)
        extractor = TextExtractor(parser)

        dialogue = extractor.get_dialogue_text()

        # Should have 2 dialogue entries
        assert len(dialogue) == 2

        # First entry should be from Euthyphro
        assert dialogue[0]["speaker"] == "Εὐθύφρων"
        assert "τί νεώτερον" in dialogue[0]["text"]

        # Second entry should be from Socrates
        assert dialogue[1]["speaker"] == "Σωκράτης"
        assert "Ἀθηναῖοί" in dialogue[1]["text"]

    def test_extract_speaker_labels(self, sample_xml_path):
        """Test 5: Should extract speaker labels (ΕΥΘ., ΣΩ.)."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        parser = TEIParser(sample_xml_path)
        extractor = TextExtractor(parser)

        dialogue = extractor.get_dialogue_text()

        # Check labels are extracted
        assert dialogue[0]["label"] == "ΕΥΘ."
        assert dialogue[1]["label"] == "ΣΩ."

    def test_extract_stephanus_numbers(self, sample_xml_path):
        """Test 6: Should extract Stephanus pagination markers."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        parser = TEIParser(sample_xml_path)
        extractor = TextExtractor(parser)

        dialogue = extractor.get_dialogue_text()

        # First dialogue should have Stephanus section marker
        # Note: Page milestones are intentionally filtered out as they're redundant
        stephanus = dialogue[0]["stephanus"]
        assert len(stephanus) == 1
        assert "2a" in stephanus  # section number

    def test_extract_handles_inline_comments(self, tmp_path):
        """Regression: inline XML comments should not break extraction."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        xml_content = textwrap.dedent(
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
            <TEI xmlns=\"http://www.tei-c.org/ns/1.0\">
              <text>
                <body>
                  <p>Intro <!-- comment -->text content</p>
                </body>
              </text>
            </TEI>
            """
        )

        xml_path = tmp_path / "comment_fixture.xml"
        xml_path.write_text(xml_content, encoding="utf-8")

        parser = TEIParser(xml_path)
        extractor = TextExtractor(parser)

        dialogue = extractor.get_dialogue_text()

        assert len(dialogue) == 1
        assert dialogue[0]["text"] == "Intro text content"

    def test_handle_editorial_markup(self, sample_xml_path):
        """Test 7: Should handle editorial markup like <del> tags."""
        # We'll create a fixture with <del> tags for this test
        # For now, test basic text extraction without errors
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        parser = TEIParser(sample_xml_path)
        extractor = TextExtractor(parser)

        # Should not raise any errors
        dialogue = extractor.get_dialogue_text()
        assert len(dialogue) > 0

    def test_maintain_dialogue_order(self, sample_xml_path):
        """Test that dialogue text is extracted in document order."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        parser = TEIParser(sample_xml_path)
        extractor = TextExtractor(parser)

        dialogue = extractor.get_dialogue_text()

        # Should maintain order: Euthyphro first, then Socrates
        speakers = [entry["speaker"] for entry in dialogue]
        assert speakers == ["Εὐθύφρων", "Σωκράτης"]

    def test_extract_from_real_euthyphro(self, euthyphro_xml_path):
        """Test extraction from the actual Euthyphro XML file."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        if not euthyphro_xml_path.exists():
            pytest.skip("Euthyphro XML file not found")

        parser = TEIParser(euthyphro_xml_path)
        extractor = TextExtractor(parser)

        dialogue = extractor.get_dialogue_text()

        # Should have many dialogue entries
        assert len(dialogue) > 10

        # All entries should have required fields
        for entry in dialogue:
            assert "speaker" in entry
            assert "label" in entry
            assert "text" in entry
            assert "stephanus" in entry

    def test_extract_from_empty_file_raises_error(self):
        """Test that extractor raises EmptyExtractionError for file with no extractable text."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor
        from exeuresis.exceptions import EmptyExtractionError

        empty_xml = Path(__file__).parent / "fixtures" / "invalid" / "empty_text.xml"

        parser = TEIParser(empty_xml)
        extractor = TextExtractor(parser)

        with pytest.raises(EmptyExtractionError) as exc_info:
            extractor.get_dialogue_text()

        assert str(empty_xml) in str(exc_info.value)
        assert "No text" in str(exc_info.value)

    def test_extract_plutarch_stephpage_markers(self, plutarch_xml_path):
        """Test extraction of Plutarch texts with stephpage pagination markers."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        if not plutarch_xml_path.exists():
            pytest.skip("Plutarch XML file not found")

        parser = TEIParser(plutarch_xml_path)
        extractor = TextExtractor(parser)

        text_entries = extractor.get_dialogue_text()

        # Should have many entries
        assert len(text_entries) > 10

        # All entries should have required fields
        for entry in text_entries:
            assert "speaker" in entry
            assert "label" in entry
            assert "text" in entry
            assert "stephanus" in entry

        # Find entries with stephpage markers
        entries_with_markers = [e for e in text_entries if e["stephanus"]]
        assert len(entries_with_markers) > 0, "Should have entries with stephpage markers"

        # Check that markers are in expected format (e.g., "1012b", "1012c", etc.)
        all_markers = [marker for e in entries_with_markers for marker in e["stephanus"]]
        assert any("1012" in marker for marker in all_markers), "Should contain 1012 series markers"

    def test_stephanus_marker_types_support(self, euthyphro_xml_path, plutarch_xml_path):
        """Test that both unit='section' (Plato) and unit='stephpage' (Plutarch) are supported."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        if not euthyphro_xml_path.exists() or not plutarch_xml_path.exists():
            pytest.skip("Required XML files not found")

        # Test Plato (section markers)
        plato_parser = TEIParser(euthyphro_xml_path)
        plato_extractor = TextExtractor(plato_parser)
        plato_entries = plato_extractor.get_dialogue_text()
        plato_markers = [marker for e in plato_entries for marker in e["stephanus"]]
        assert len(plato_markers) > 0, "Should extract section markers from Plato"
        # Plato markers are like "2a", "2b", "3", etc.
        assert any(marker in ["2a", "2b", "2c", "2d", "3"] for marker in plato_markers[:20])

        # Test Plutarch (stephpage markers)
        plutarch_parser = TEIParser(plutarch_xml_path)
        plutarch_extractor = TextExtractor(plutarch_parser)
        plutarch_entries = plutarch_extractor.get_dialogue_text()
        plutarch_markers = [marker for e in plutarch_entries for marker in e["stephanus"]]
        assert len(plutarch_markers) > 0, "Should extract stephpage markers from Plutarch"
        # Plutarch markers are like "1012b", "1012c", "1013a", etc.
        assert any("1012" in marker or "1013" in marker for marker in plutarch_markers[:20])

    def test_extract_section_numbers_from_divs(self, sample_sections_path):
        """Test extraction of section numbers from <div subtype='section'> elements."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        parser = TEIParser(sample_sections_path)
        extractor = TextExtractor(parser)

        text_entries = extractor.get_dialogue_text()

        # Should have 3 entries (one per section)
        assert len(text_entries) == 3

        # Each entry should have the correct section number
        assert text_entries[0]["stephanus"] == ["1"]
        assert text_entries[1]["stephanus"] == ["2"]
        assert text_entries[2]["stephanus"] == ["3"]

        # Check that text content is extracted
        assert "ἀγών" in text_entries[0]["text"]
        assert "χαλεπώτατον" in text_entries[1]["text"]
        assert "διηγήσομαι" in text_entries[2]["text"]

    def test_extract_from_real_trapeziticus(self, trapeziticus_xml_path):
        """Test extraction from the actual Isocrates Trapeziticus XML file."""
        from exeuresis.parser import TEIParser
        from exeuresis.extractor import TextExtractor

        if not trapeziticus_xml_path.exists():
            pytest.skip("Trapeziticus XML file not found")

        parser = TEIParser(trapeziticus_xml_path)
        extractor = TextExtractor(parser)

        text_entries = extractor.get_dialogue_text()

        # Should have many entries (Trapeziticus has 58 sections)
        assert len(text_entries) == 58

        # All entries should have required fields
        for entry in text_entries:
            assert "speaker" in entry
            assert "label" in entry
            assert "text" in entry
            assert "stephanus" in entry

        # Find entries with section markers
        entries_with_markers = [e for e in text_entries if e["stephanus"]]
        assert len(entries_with_markers) == 58, "Should have section markers for all sections"

        # Check that first few section markers are correct
        assert text_entries[0]["stephanus"] == ["1"]
        assert text_entries[1]["stephanus"] == ["2"]
        assert text_entries[2]["stephanus"] == ["3"]

        # Check that text content is extracted from first section
        assert "ἀγών" in text_entries[0]["text"]
