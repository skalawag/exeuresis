"""Range filtering for Stephanus pagination and other milestone systems."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict


class RangeType(Enum):
    """Types of Stephanus ranges."""
    SINGLE_SECTION = "single_section"  # e.g., "327a"
    SINGLE_PAGE = "single_page"        # e.g., "327"
    SECTION_RANGE = "section_range"    # e.g., "327a-328c"
    PAGE_RANGE = "page_range"          # e.g., "327-329"


@dataclass
class RangeSpec:
    """Specification for a Stephanus range."""
    start: str
    end: str
    range_type: RangeType

    @property
    def is_single(self) -> bool:
        """True if this is a single section or page (not a range)."""
        return self.range_type in (RangeType.SINGLE_SECTION, RangeType.SINGLE_PAGE)

    @property
    def is_page_range(self) -> bool:
        """True if this is a page-based range (not section-specific)."""
        return self.range_type in (RangeType.SINGLE_PAGE, RangeType.PAGE_RANGE)


class StephanusRangeParser:
    """Parse Stephanus range specifications."""

    # Pattern for Stephanus markers: page number optionally followed by section letter
    MARKER_PATTERN = re.compile(r'^(\d+)([a-z])?$')

    def parse(self, range_spec: str) -> RangeSpec:
        """
        Parse a range specification string.

        Args:
            range_spec: Range specification (e.g., "327a", "327-329", "327a-328c")

        Returns:
            RangeSpec object

        Raises:
            ValueError: If range format is invalid
        """
        if not range_spec or not range_spec.strip():
            raise ValueError("Empty range specification")

        range_spec = range_spec.strip()

        # Check if it's a range (contains hyphen)
        if '-' in range_spec:
            parts = range_spec.split('-')
            if len(parts) != 2:
                raise ValueError(f"Invalid range format: '{range_spec}' (multiple hyphens)")

            start = parts[0].strip()
            end = parts[1].strip()

            # Validate both parts
            if not self._is_valid_marker(start) or not self._is_valid_marker(end):
                raise ValueError(f"Invalid range format: '{range_spec}'")

            # Determine if it's a page range or section range
            start_has_section = self._has_section_letter(start)
            end_has_section = self._has_section_letter(end)

            if start_has_section or end_has_section:
                # At least one has a section letter → section range
                return RangeSpec(start=start, end=end, range_type=RangeType.SECTION_RANGE)
            else:
                # Both are just numbers → page range
                return RangeSpec(start=start, end=end, range_type=RangeType.PAGE_RANGE)
        else:
            # Single marker
            if not self._is_valid_marker(range_spec):
                raise ValueError(f"Invalid range format: '{range_spec}'")

            if self._has_section_letter(range_spec):
                return RangeSpec(start=range_spec, end=range_spec, range_type=RangeType.SINGLE_SECTION)
            else:
                return RangeSpec(start=range_spec, end=range_spec, range_type=RangeType.SINGLE_PAGE)

    def _is_valid_marker(self, marker: str) -> bool:
        """Check if a marker matches the Stephanus pattern."""
        return bool(self.MARKER_PATTERN.match(marker))

    def _has_section_letter(self, marker: str) -> bool:
        """Check if a marker has a section letter."""
        match = self.MARKER_PATTERN.match(marker)
        return match and match.group(2) is not None
