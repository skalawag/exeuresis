"""Tests for anthology data structures."""

import pytest
from exeuresis.anthology_extractor import PassageSpec, AnthologyBlock


def test_passage_spec_creation():
    """Test creating PassageSpec."""
    spec = PassageSpec(
        work_id="tlg0059.tlg001",
        ranges=["5a", "7b-c", "8"]
    )
    assert spec.work_id == "tlg0059.tlg001"
    assert spec.ranges == ["5a", "7b-c", "8"]


def test_anthology_block_creation():
    """Test creating AnthologyBlock."""
    block = AnthologyBlock(
        work_title_en="Euthyphro",
        work_title_gr="Εὐθύφρων",
        range_display="5a",
        segments=[{"text": "Sample", "stephanus": ["5a"]}],
        book=None
    )
    assert block.work_title_en == "Euthyphro"
    assert block.work_title_gr == "Εὐθύφρων"
    assert block.range_display == "5a"
    assert block.book is None


def test_anthology_block_format_header_no_book():
    """Test formatting header without book."""
    block = AnthologyBlock(
        work_title_en="Euthyphro",
        work_title_gr="Εὐθύφρων",
        range_display="5a",
        segments=[],
        book=None
    )
    header = block.format_header(width=79)

    assert "Euthyphro (Εὐθύφρων) 5a" in header
    assert "-" * 79 in header


def test_anthology_block_format_header_with_book():
    """Test formatting header with book number."""
    block = AnthologyBlock(
        work_title_en="Republic",
        work_title_gr="Πολιτεία",
        range_display="354b-c",
        segments=[],
        book="1"
    )
    header = block.format_header(width=79)

    # Should show "1.354b-c" format
    assert "Republic (Πολιτεία) 1.354b-c" in header
    assert "-" * 79 in header
