"""Tests for Stephanus range filtering."""

import pytest
from exeuresis.range_filter import RangeSpec, RangeType, StephanusRangeParser, StephanusComparator, RangeFilter
from exeuresis.exceptions import InvalidStephanusRangeError


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

    def test_parse_section_range_shorthand_end(self):
        """Test parsing shorthand section range like '327a-c'."""
        parser = StephanusRangeParser()
        spec = parser.parse("327a-c")
        assert spec.start == "327a"
        assert spec.end == "327c"
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


class TestRangeFilter:
    """Tests for filtering dialogue segments by Stephanus range."""

    def setup_method(self):
        """Create sample dialogue data for testing."""
        self.sample_dialogue = [
            {"speaker": "Σωκράτης", "label": "ΣΩ.", "text": "Text at 327a", "stephanus": ["327", "327a"], "said_id": 0},
            {"speaker": "Γλαύκων", "label": "ΓΛ.", "text": "Text at 327b", "stephanus": ["327b"], "said_id": 1},
            {"speaker": "Σωκράτης", "label": "ΣΩ.", "text": "Text at 327c", "stephanus": ["327c"], "said_id": 2},
            {"speaker": "Γλαύκων", "label": "ΓΛ.", "text": "Text at 328a", "stephanus": ["328", "328a"], "said_id": 3},
            {"speaker": "Σωκράτης", "label": "ΣΩ.", "text": "Text at 328b", "stephanus": ["328b"], "said_id": 4},
            {"speaker": "Γλαύκων", "label": "ΓΛ.", "text": "Text at 329a", "stephanus": ["329", "329a"], "said_id": 5},
        ]

    def test_filter_single_section(self):
        """Test filtering to a single section."""
        filter_obj = RangeFilter()
        result = filter_obj.filter(self.sample_dialogue, "327b")
        assert len(result) == 1
        assert result[0]["text"] == "Text at 327b"
        assert result[0]["stephanus"] == ["327b"]

    def test_filter_single_page(self):
        """Test filtering to all sections from a single page."""
        filter_obj = RangeFilter()
        result = filter_obj.filter(self.sample_dialogue, "327")
        assert len(result) == 3
        assert result[0]["stephanus"] == ["327", "327a"]
        assert result[1]["stephanus"] == ["327b"]
        assert result[2]["stephanus"] == ["327c"]

    def test_filter_section_range(self):
        """Test filtering to a section range."""
        filter_obj = RangeFilter()
        result = filter_obj.filter(self.sample_dialogue, "327b-328a")
        assert len(result) == 3
        assert result[0]["text"] == "Text at 327b"
        assert result[1]["text"] == "Text at 327c"
        assert result[2]["text"] == "Text at 328a"

    def test_filter_page_range(self):
        """Test filtering to a page range."""
        filter_obj = RangeFilter()
        result = filter_obj.filter(self.sample_dialogue, "327-328")
        assert len(result) == 5
        # Should include all of 327 and 328
        assert result[0]["stephanus"] == ["327", "327a"]
        assert result[-1]["stephanus"] == ["328b"]

    def test_filter_range_inclusive_end(self):
        """Test that range end is inclusive."""
        filter_obj = RangeFilter()
        result = filter_obj.filter(self.sample_dialogue, "327a-327c")
        assert len(result) == 3
        # Should include 327c (end is inclusive)
        assert result[-1]["stephanus"] == ["327c"]

    def test_filter_shorthand_section_range(self):
        """Test filtering using shorthand notation like '327a-c'."""
        filter_obj = RangeFilter()
        result = filter_obj.filter(self.sample_dialogue, "327a-c")
        assert len(result) == 3
        assert result[0]["text"] == "Text at 327a"
        assert result[-1]["text"] == "Text at 327c"

    def test_filter_nonexistent_range_raises_error(self):
        """Test that filtering to nonexistent range raises error."""
        filter_obj = RangeFilter()
        with pytest.raises(InvalidStephanusRangeError, match="999z"):
            filter_obj.filter(self.sample_dialogue, "999z")

    def test_filter_empty_dialogue_raises_error(self):
        """Test that filtering empty dialogue raises error."""
        filter_obj = RangeFilter()
        with pytest.raises(InvalidStephanusRangeError, match="No segments found"):
            filter_obj.filter([], "327a")

    def test_filter_cross_book_range(self):
        """Test filtering range that spans multiple books."""
        # Simulate Republic Book 1 ending at 354c, Book 2 starting at 357a
        multi_book_dialogue = [
            {"speaker": "Σωκράτης", "label": "ΣΩ.", "text": "Book 1 at 354a", "stephanus": ["354a"], "book": "1"},
            {"speaker": "Γλαύκων", "label": "ΓΛ.", "text": "Book 1 at 354c", "stephanus": ["354c"], "book": "1"},
            {"speaker": "", "label": "", "text": "ΠΟΛΙΤΕΙΑ Β", "stephanus": [], "book": "2"},  # Book header
            {"speaker": "Σωκράτης", "label": "ΣΩ.", "text": "Book 2 at 357a", "stephanus": ["357", "357a"], "book": "2"},
            {"speaker": "Γλαύκων", "label": "ΓΛ.", "text": "Book 2 at 357b", "stephanus": ["357b"], "book": "2"},
        ]

        filter_obj = RangeFilter()
        result = filter_obj.filter(multi_book_dialogue, "354a-357b")

        # Should include 4 entries (book header without marker is excluded)
        assert len(result) == 4
        assert result[0]["text"] == "Book 1 at 354a"
        assert result[1]["text"] == "Book 1 at 354c"
        # Book header excluded since it has no markers
        assert result[2]["text"] == "Book 2 at 357a"
        assert result[3]["text"] == "Book 2 at 357b"

    def test_filter_preserves_segments_without_stephanus(self):
        """Test that segments without Stephanus markers inside range are preserved."""
        dialogue_with_gaps = [
            {"speaker": "Σωκράτης", "label": "ΣΩ.", "text": "At 327a", "stephanus": ["327a"]},
            {"speaker": "", "label": "", "text": "Title without marker", "stephanus": []},  # Should be excluded
            {"speaker": "Γλαύκων", "label": "ΓΛ.", "text": "At 327b", "stephanus": ["327b"]},
        ]

        filter_obj = RangeFilter()
        result = filter_obj.filter(dialogue_with_gaps, "327a-327b")

        # Should only include segments with stephanus markers in range
        assert len(result) == 2
        assert result[0]["text"] == "At 327a"
        assert result[1]["text"] == "At 327b"
