"""Tests for custom exceptions."""

import pytest
from exeuresis.exceptions import InvalidStephanusRangeError


def test_invalid_stephanus_range_error_basic():
    """Test InvalidStephanusRangeError with basic message."""
    error = InvalidStephanusRangeError("tlg0059.tlg001", "999z")
    assert "999z" in str(error)
    assert "tlg0059.tlg001" in str(error)
    assert error.work_id == "tlg0059.tlg001"
    assert error.range_spec == "999z"


def test_invalid_stephanus_range_error_with_reason():
    """Test InvalidStephanusRangeError with detailed reason."""
    error = InvalidStephanusRangeError(
        "tlg0059.tlg001",
        "5a-3c",
        "Start marker (5a) comes after end marker (3c)"
    )
    assert "5a-3c" in str(error)
    assert "Start marker" in str(error)
