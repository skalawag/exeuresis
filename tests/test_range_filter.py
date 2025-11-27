"""Tests for Stephanus range filtering."""

import pytest
from pi_grapheion.range_filter import RangeSpec, RangeType, StephanusRangeParser, StephanusComparator


def test_range_spec_single_section():
    """Test RangeSpec for single section like '327a'."""
    spec = RangeSpec(start="327a", end="327a", range_type=RangeType.SINGLE_SECTION)
    assert spec.start == "327a"
    assert spec.end == "327a"
    assert spec.range_type == RangeType.SINGLE_SECTION
    assert spec.is_single is True
    assert spec.is_page_range is False


def test_range_spec_single_page():
    """Test RangeSpec for single page like '327'."""
    spec = RangeSpec(start="327", end="327", range_type=RangeType.SINGLE_PAGE)
    assert spec.start == "327"
    assert spec.end == "327"
    assert spec.range_type == RangeType.SINGLE_PAGE
    assert spec.is_single is True
    assert spec.is_page_range is True


def test_range_spec_section_range():
    """Test RangeSpec for section range like '327a-328c'."""
    spec = RangeSpec(start="327a", end="328c", range_type=RangeType.SECTION_RANGE)
    assert spec.start == "327a"
    assert spec.end == "328c"
    assert spec.range_type == RangeType.SECTION_RANGE
    assert spec.is_single is False
    assert spec.is_page_range is False


def test_range_spec_page_range():
    """Test RangeSpec for page range like '327-329'."""
    spec = RangeSpec(start="327", end="329", range_type=RangeType.PAGE_RANGE)
    assert spec.start == "327"
    assert spec.end == "329"
    assert spec.range_type == RangeType.PAGE_RANGE
    assert spec.is_single is False
    assert spec.is_page_range is True


class TestStephanusRangeParser:
    """Tests for parsing range specifications."""

    def test_parse_single_section(self):
        """Test parsing single section like '327a'."""
        parser = StephanusRangeParser()
        spec = parser.parse("327a")
        assert spec.start == "327a"
        assert spec.end == "327a"
        assert spec.range_type == RangeType.SINGLE_SECTION

    def test_parse_single_page(self):
        """Test parsing single page like '327'."""
        parser = StephanusRangeParser()
        spec = parser.parse("327")
        assert spec.start == "327"
        assert spec.end == "327"
        assert spec.range_type == RangeType.SINGLE_PAGE

    def test_parse_section_range(self):
        """Test parsing section range like '327a-328c'."""
        parser = StephanusRangeParser()
        spec = parser.parse("327a-328c")
        assert spec.start == "327a"
        assert spec.end == "328c"
        assert spec.range_type == RangeType.SECTION_RANGE

    def test_parse_page_range(self):
        """Test parsing page range like '327-329'."""
        parser = StephanusRangeParser()
        spec = parser.parse("327-329")
        assert spec.start == "327"
        assert spec.end == "329"
        assert spec.range_type == RangeType.PAGE_RANGE

    def test_parse_single_section_page_range(self):
        """Test parsing same-page section range like '5a-5e'."""
        parser = StephanusRangeParser()
        spec = parser.parse("5a-5e")
        assert spec.start == "5a"
        assert spec.end == "5e"
        assert spec.range_type == RangeType.SECTION_RANGE

    def test_parse_invalid_format(self):
        """Test parsing invalid format raises ValueError."""
        parser = StephanusRangeParser()
        with pytest.raises(ValueError, match="Invalid range format"):
            parser.parse("abc-xyz-123")

    def test_parse_empty_string(self):
        """Test parsing empty string raises ValueError."""
        parser = StephanusRangeParser()
        with pytest.raises(ValueError, match="Empty range specification"):
            parser.parse("")


class TestStephanusComparator:
    """Tests for comparing Stephanus markers."""

    def test_compare_same_markers(self):
        """Test comparing identical markers."""
        comp = StephanusComparator()
        assert comp.compare("327a", "327a") == 0

    def test_compare_different_sections_same_page(self):
        """Test comparing different sections on same page."""
        comp = StephanusComparator()
        assert comp.compare("327a", "327b") < 0
        assert comp.compare("327b", "327a") > 0
        assert comp.compare("327a", "327e") < 0

    def test_compare_different_pages(self):
        """Test comparing markers on different pages."""
        comp = StephanusComparator()
        assert comp.compare("327a", "328a") < 0
        assert comp.compare("328a", "327a") > 0
        assert comp.compare("50b", "51a") < 0

    def test_compare_page_to_section(self):
        """Test comparing page marker to section marker."""
        comp = StephanusComparator()
        # Page marker (327) should be treated as start of that page (327a)
        assert comp.compare("327", "327a") <= 0
        assert comp.compare("327", "327b") < 0
        assert comp.compare("328", "327e") > 0

    def test_extract_page_number(self):
        """Test extracting page number from marker."""
        comp = StephanusComparator()
        assert comp.extract_page_number("327a") == 327
        assert comp.extract_page_number("327") == 327
        assert comp.extract_page_number("5b") == 5

    def test_extract_section_letter(self):
        """Test extracting section letter from marker."""
        comp = StephanusComparator()
        assert comp.extract_section_letter("327a") == "a"
        assert comp.extract_section_letter("327") == ""
        assert comp.extract_section_letter("5e") == "e"
