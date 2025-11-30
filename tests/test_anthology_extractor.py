"""Tests for anthology extractor core logic."""

from pathlib import Path

import pytest

from exeuresis.anthology_extractor import (
    AnthologyExtractor,
    PassageSpec,
)
from exeuresis.exceptions import WorkNotFoundError


class TestAnthologyExtractor:
    """Tests for AnthologyExtractor class."""

    def test_extract_single_work_single_range(self):
        """Test extracting single range from single work."""
        extractor = AnthologyExtractor()
        passages = [PassageSpec(work_id="tlg0059.tlg001", ranges=["5a"])]

        blocks = extractor.extract_passages(passages)

        assert len(blocks) == 1
        assert blocks[0].work_title_en == "Euthyphro"
        assert blocks[0].work_title_gr == "Εὐθύφρων"
        assert blocks[0].range_display == "5a"
        assert len(blocks[0].segments) > 0

    def test_extract_single_work_multiple_ranges(self):
        """Test extracting multiple discontinuous ranges from single work."""
        extractor = AnthologyExtractor()
        passages = [PassageSpec(work_id="tlg0059.tlg001", ranges=["5a", "7b-7c"])]

        blocks = extractor.extract_passages(passages)

        # Should produce 2 separate blocks
        assert len(blocks) == 2
        assert blocks[0].range_display == "5a"
        assert blocks[1].range_display == "7b-7c"

    def test_extract_multiple_works(self):
        """Test extracting passages from multiple works."""
        extractor = AnthologyExtractor()
        passages = [
            PassageSpec(work_id="tlg0059.tlg001", ranges=["5a"]),
            PassageSpec(work_id="tlg0059.tlg030", ranges=["354b"]),
        ]

        blocks = extractor.extract_passages(passages)

        assert len(blocks) == 2
        assert blocks[0].work_title_en == "Euthyphro"
        assert blocks[1].work_title_en == "Republic"

    def test_extract_preserves_book_number(self):
        """Test that book numbers are preserved for multi-book works."""
        extractor = AnthologyExtractor()
        passages = [PassageSpec(work_id="tlg0059.tlg030", ranges=["354b"])]

        blocks = extractor.extract_passages(passages)

        assert len(blocks) == 1
        assert blocks[0].book == "1"  # Republic 354b is in Book 1

    def test_extract_invalid_work_raises_error(self):
        """Test extracting from invalid work ID raises error."""
        extractor = AnthologyExtractor()
        passages = [PassageSpec(work_id="tlg9999.tlg999", ranges=["5a"])]

        with pytest.raises(WorkNotFoundError):
            extractor.extract_passages(passages)

    def test_extract_with_custom_data_dir(self, tmp_path):
        """Test using custom data directory."""
        # This test verifies the data_dir parameter works
        extractor = AnthologyExtractor(data_dir=Path("canonical-greekLit/data"))
        passages = [PassageSpec(work_id="tlg0059.tlg001", ranges=["5a"])]

        blocks = extractor.extract_passages(passages)
        assert len(blocks) == 1
