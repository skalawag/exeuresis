"""Range filtering for Stephanus pagination and other milestone systems."""

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
