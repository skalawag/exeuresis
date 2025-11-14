"""Tests for text extraction functionality."""

import pytest
from pathlib import Path

# from pi_grapheion.extractor import TextExtractor
# from pi_grapheion.parser import TEIParser


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

    def test_extract_dialogue_text(self, sample_xml_path):
        """Test 4: Should extract text from <said> elements."""
        from pi_grapheion.parser import TEIParser
        from pi_grapheion.extractor import TextExtractor

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
        from pi_grapheion.parser import TEIParser
        from pi_grapheion.extractor import TextExtractor

        parser = TEIParser(sample_xml_path)
        extractor = TextExtractor(parser)

        dialogue = extractor.get_dialogue_text()

        # Check labels are extracted
        assert dialogue[0]["label"] == "ΕΥΘ."
        assert dialogue[1]["label"] == "ΣΩ."

    def test_extract_stephanus_numbers(self, sample_xml_path):
        """Test 6: Should extract Stephanus pagination markers."""
        from pi_grapheion.parser import TEIParser
        from pi_grapheion.extractor import TextExtractor

        parser = TEIParser(sample_xml_path)
        extractor = TextExtractor(parser)

        dialogue = extractor.get_dialogue_text()

        # First dialogue should have Stephanus section marker
        # Note: Page milestones are intentionally filtered out as they're redundant
        stephanus = dialogue[0]["stephanus"]
        assert len(stephanus) == 1
        assert "2a" in stephanus  # section number

    def test_handle_editorial_markup(self, sample_xml_path):
        """Test 7: Should handle editorial markup like <del> tags."""
        # We'll create a fixture with <del> tags for this test
        # For now, test basic text extraction without errors
        from pi_grapheion.parser import TEIParser
        from pi_grapheion.extractor import TextExtractor

        parser = TEIParser(sample_xml_path)
        extractor = TextExtractor(parser)

        # Should not raise any errors
        dialogue = extractor.get_dialogue_text()
        assert len(dialogue) > 0

    def test_maintain_dialogue_order(self, sample_xml_path):
        """Test that dialogue text is extracted in document order."""
        from pi_grapheion.parser import TEIParser
        from pi_grapheion.extractor import TextExtractor

        parser = TEIParser(sample_xml_path)
        extractor = TextExtractor(parser)

        dialogue = extractor.get_dialogue_text()

        # Should maintain order: Euthyphro first, then Socrates
        speakers = [entry["speaker"] for entry in dialogue]
        assert speakers == ["Εὐθύφρων", "Σωκράτης"]

    def test_extract_from_real_euthyphro(self, euthyphro_xml_path):
        """Test extraction from the actual Euthyphro XML file."""
        from pi_grapheion.parser import TEIParser
        from pi_grapheion.extractor import TextExtractor

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
        from pi_grapheion.parser import TEIParser
        from pi_grapheion.extractor import TextExtractor
        from pi_grapheion.exceptions import EmptyExtractionError

        empty_xml = Path(__file__).parent / "fixtures" / "invalid" / "empty_text.xml"

        parser = TEIParser(empty_xml)
        extractor = TextExtractor(parser)

        with pytest.raises(EmptyExtractionError) as exc_info:
            extractor.get_dialogue_text()

        assert str(empty_xml) in str(exc_info.value)
        assert "No text" in str(exc_info.value)
