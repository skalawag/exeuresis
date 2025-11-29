"""Anthology extraction for discontinuous passages."""

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

from exeuresis.catalog import PerseusCatalog
from exeuresis.parser import TEIParser
from exeuresis.extractor import TextExtractor
from exeuresis.range_filter import RangeFilter
from exeuresis.exceptions import WorkNotFoundError


def parse_range_list(range_str: str) -> List[str]:
    """
    Parse comma-separated range list into individual ranges.

    Args:
        range_str: Comma-separated ranges (e.g., "5a, 7b-c, 8")

    Returns:
        List of individual ranges

    Raises:
        ValueError: If range_str is empty or whitespace-only

    Examples:
        >>> parse_range_list("5a, 7b-c, 8")
        ["5a", "7b-c", "8"]
        >>> parse_range_list("5a,7b-c,8")
        ["5a", "7b-c", "8"]
    """
    # Strip and check for empty
    range_str = range_str.strip()
    if not range_str:
        raise ValueError("Range list cannot be empty")

    # Split on comma and strip each part
    ranges = [r.strip() for r in range_str.split(",")]

    # Filter out any empty strings
    ranges = [r for r in ranges if r]

    return ranges


@dataclass
class PassageSpec:
    """Specification for passages to extract from a work."""

    work_id: str
    ranges: List[str]  # e.g., ["5a", "7b-c", "8"]


@dataclass
class AnthologyBlock:
    """A block of text with header for anthology output."""

    work_title_en: str
    work_title_gr: str
    range_display: str
    segments: List[Dict]
    book: Optional[str] = None

    def format_header(self, width: Optional[int] = 79) -> str:
        """
        Format a header for the anthology block.

        Args:
            width: Width of the separator line (default: 79)

        Returns:
            Formatted header with title, range, and separator
        """
        # Format: "Work Title (Greek Title) range"
        # If book number exists, show as "1.354b-c" format
        if self.book:
            range_part = f"{self.book}.{self.range_display}"
        else:
            range_part = self.range_display

        header_line = f"{self.work_title_en} ({self.work_title_gr}) {range_part}"
        if width is None:
            separator_width = max(len(header_line), 79)
        else:
            separator_width = max(width, 1)

        separator = "-" * separator_width

        return f"{header_line}\n{separator}"


class AnthologyExtractor:
    """Extract anthology passages from multiple works and ranges."""

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize AnthologyExtractor.

        Args:
            data_dir: Path to canonical-greekLit data directory
                     (defaults to canonical-greekLit/data)
        """
        self.catalog = PerseusCatalog()
        self.data_dir = data_dir or Path("canonical-greekLit/data")
        self.range_filter = RangeFilter()

    def extract_passages(self, passages: List[PassageSpec]) -> List[AnthologyBlock]:
        """
        Extract passages from multiple works.

        Args:
            passages: List of PassageSpec defining what to extract

        Returns:
            List of AnthologyBlock objects, one per range

        Raises:
            WorkNotFoundError: If a work ID is invalid
        """
        blocks = []

        for passage in passages:
            # Resolve work ID to file path
            xml_file = self.catalog.resolve_work_id(passage.work_id)

            # Get work metadata
            work_info = self._get_work_info(passage.work_id)

            # Parse the XML file
            parser = TEIParser(xml_file)
            extractor = TextExtractor(parser)
            all_segments = extractor.get_dialogue_text()

            # Extract each range as a separate block
            for range_spec in passage.ranges:
                filtered_segments = self.range_filter.filter(
                    all_segments, range_spec, passage.work_id
                )

                # Determine book number (if any)
                book = self._get_book_number(filtered_segments)

                # Create anthology block
                block = AnthologyBlock(
                    work_title_en=work_info["title_en"],
                    work_title_gr=work_info["title_gr"],
                    range_display=range_spec,
                    segments=filtered_segments,
                    book=book,
                )
                blocks.append(block)

        return blocks

    def _get_work_info(self, work_id: str) -> Dict[str, str]:
        """
        Get work metadata from catalog.

        Args:
            work_id: Work ID (e.g., "tlg0059.tlg001")

        Returns:
            Dictionary with title_en and title_gr
        """
        # Split work ID
        author_id, work_num = work_id.split(".")

        # Get author
        authors = self.catalog.list_authors()
        author = None
        for a in authors:
            if a.tlg_id == author_id:
                author = a
                break

        if not author:
            raise WorkNotFoundError(work_id, f"Author {author_id} not found")

        # Get work
        works = self.catalog.list_works(author_id)
        for work in works:
            if work.work_id == work_num:
                return {
                    "title_en": work.title_en or "Unknown",
                    "title_gr": work.title_grc or "Unknown",
                }

        raise WorkNotFoundError(work_id, f"Work {work_num} not found for author {author_id}")

    def _get_book_number(self, segments: List[Dict]) -> Optional[str]:
        """
        Get book number from segments if present.

        Args:
            segments: List of dialogue segments

        Returns:
            Book number as string, or None if no book field
        """
        # Check first segment for book number
        if segments and "book" in segments[0]:
            return segments[0]["book"]
        return None
