"""Anthology extraction for discontinuous passages."""

from dataclasses import dataclass
from typing import List, Dict, Optional


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

    def format_header(self, width: int = 79) -> str:
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
        separator = "-" * width

        return f"{header_line}\n{separator}"
