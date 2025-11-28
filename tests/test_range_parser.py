"""Tests for range list parsing."""

import pytest
from exeuresis.anthology_extractor import parse_range_list


def test_parse_single_range():
    """Test parsing a single Stephanus range."""
    result = parse_range_list("5a")
    assert result == ["5a"]


def test_parse_multiple_ranges_with_commas():
    """Test parsing comma-separated ranges."""
    result = parse_range_list("5a, 7b-c, 8")
    assert result == ["5a", "7b-c", "8"]


def test_parse_multiple_ranges_without_spaces():
    """Test parsing comma-separated ranges without spaces."""
    result = parse_range_list("5a,7b-c,8")
    assert result == ["5a", "7b-c", "8"]


def test_parse_ranges_mixed_spacing():
    """Test parsing with inconsistent spacing."""
    result = parse_range_list("5a,7b-c, 8, 10a-b")
    assert result == ["5a", "7b-c", "8", "10a-b"]


def test_parse_ranges_with_extra_whitespace():
    """Test parsing with extra whitespace."""
    result = parse_range_list("  5a  ,  7b-c  ,  8  ")
    assert result == ["5a", "7b-c", "8"]


def test_parse_empty_string():
    """Test parsing empty string raises error."""
    with pytest.raises(ValueError, match="Range list cannot be empty"):
        parse_range_list("")


def test_parse_whitespace_only():
    """Test parsing whitespace-only string raises error."""
    with pytest.raises(ValueError, match="Range list cannot be empty"):
        parse_range_list("   ")
