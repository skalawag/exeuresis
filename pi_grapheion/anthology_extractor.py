"""Anthology extraction for discontinuous passages."""

from dataclasses import dataclass
from typing import List, Dict, Optional


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
