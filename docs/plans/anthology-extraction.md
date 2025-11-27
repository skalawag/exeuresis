# Anthology Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add anthology extraction feature to support discontinuous passages within and across works, with work name aliases.

**Architecture:** Add three new modules: `work_resolver.py` (alias resolution), `anthology_extractor.py` (multi-passage extraction), and `anthology_formatter.py` (block formatting). Modify CLI to support `--passages` flag with multiple work/passage pairs.

**Tech Stack:** Python 3.x, YAML for config files, existing pi_grapheion architecture (Parser → Extractor → RangeFilter → Formatter)

**Style Restriction:** Anthology extraction supports only styles A-D. Styles E (scriptio continua) and S (Stephanus layout) are incompatible with the multi-block anthology format and will raise `InvalidStyleError`.

---

## Task 1: Create WorkResolver for Alias Resolution

**Files:**
- Create: `pi_grapheion/work_resolver.py`
- Create: `tests/test_work_resolver.py`

**Step 1: Write the failing test**

Create `tests/test_work_resolver.py`:

```python
"""Tests for work name resolution and aliases."""

import pytest
from pathlib import Path
from pi_grapheion.work_resolver import WorkResolver
from pi_grapheion.exceptions import WorkNotFoundError


class TestWorkResolver:
    """Tests for WorkResolver alias system."""

    def test_resolve_exact_tlg_id(self):
        """Test resolving exact TLG ID passes through."""
        resolver = WorkResolver()
        assert resolver.resolve("tlg0059.tlg001") == "tlg0059.tlg001"

    def test_resolve_work_by_english_title(self):
        """Test resolving work by English title."""
        resolver = WorkResolver()
        # Case-insensitive
        assert resolver.resolve("euthyphro") == "tlg0059.tlg001"
        assert resolver.resolve("Euthyphro") == "tlg0059.tlg001"
        assert resolver.resolve("EUTHYPHRO") == "tlg0059.tlg001"

    def test_resolve_work_by_greek_title(self):
        """Test resolving work by Greek title."""
        resolver = WorkResolver()
        result = resolver.resolve("Εὐθύφρων")
        assert result == "tlg0059.tlg001"

    def test_resolve_work_with_extracted_alias(self):
        """Test resolving work using extracted alias."""
        resolver = WorkResolver()
        # "Republic" should resolve
        result = resolver.resolve("republic")
        assert result == "tlg0059.tlg030"

    def test_resolve_ambiguous_name_raises_error(self):
        """Test ambiguous name raises error with suggestions."""
        resolver = WorkResolver()
        with pytest.raises(WorkNotFoundError) as exc_info:
            # If there are multiple matches, should fail
            resolver.resolve("nonexistent_work")
        assert "nonexistent_work" in str(exc_info.value)

    def test_resolve_with_user_config(self, tmp_path):
        """Test user-defined aliases from config file."""
        # Create test config
        config_file = tmp_path / "aliases.yaml"
        config_file.write_text("""
aliases:
  euth: tlg0059.tlg001
  rep: tlg0059.tlg030
""")

        resolver = WorkResolver(config_path=config_file)
        assert resolver.resolve("euth") == "tlg0059.tlg001"
        assert resolver.resolve("rep") == "tlg0059.tlg030"

    def test_project_config_overrides_user_config(self, tmp_path):
        """Test project config overrides user config."""
        user_config = tmp_path / "user_aliases.yaml"
        user_config.write_text("""
aliases:
  mywork: tlg0059.tlg001
""")

        project_config = tmp_path / "project_aliases.yaml"
        project_config.write_text("""
aliases:
  mywork: tlg0059.tlg030  # Override
""")

        resolver = WorkResolver(
            user_config_path=user_config,
            project_config_path=project_config
        )
        # Project config should override
        assert resolver.resolve("mywork") == "tlg0059.tlg030"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_work_resolver.py -v`
Expected: `ImportError: cannot import name 'WorkResolver'` or `FAIL`

**Step 3: Write minimal implementation**

Create `pi_grapheion/work_resolver.py`:

```python
"""Work name resolution with alias support."""

import logging
from pathlib import Path
from typing import Dict, Optional
import yaml

from pi_grapheion.catalog import PerseusCatalog
from pi_grapheion.exceptions import WorkNotFoundError

logger = logging.getLogger(__name__)


class WorkResolver:
    """Resolve work names to TLG IDs using aliases and catalog lookup."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        user_config_path: Optional[Path] = None,
        project_config_path: Optional[Path] = None,
    ):
        """
        Initialize WorkResolver with optional config paths.

        Args:
            config_path: Single config file (for testing)
            user_config_path: User config (~/.pi-grapheion/aliases.yaml)
            project_config_path: Project config (.pi-grapheion/aliases.yaml)
        """
        self.catalog = PerseusCatalog()
        self.aliases: Dict[str, str] = {}

        # Load aliases in order: extracted, user, project (project overrides)
        self._load_extracted_aliases()

        if config_path:
            # Single config for testing
            self._load_config_file(config_path)
        else:
            # Load user config first
            if user_config_path:
                self._load_config_file(user_config_path)
            elif Path.home().joinpath(".pi-grapheion", "aliases.yaml").exists():
                self._load_config_file(
                    Path.home() / ".pi-grapheion" / "aliases.yaml"
                )

            # Load project config second (overrides user)
            if project_config_path:
                self._load_config_file(project_config_path)
            elif Path(".pi-grapheion/aliases.yaml").exists():
                self._load_config_file(Path(".pi-grapheion/aliases.yaml"))

    def resolve(self, name: str) -> str:
        """
        Resolve a work name to TLG ID.

        Args:
            name: Work name (title, alias, or TLG ID)

        Returns:
            TLG ID (e.g., "tlg0059.tlg001")

        Raises:
            WorkNotFoundError: If name cannot be resolved
        """
        # If already a valid TLG ID, pass through
        if self._is_tlg_id(name):
            return name

        # Try aliases (case-insensitive)
        name_lower = name.lower()
        if name_lower in self.aliases:
            return self.aliases[name_lower]

        # Not found
        raise WorkNotFoundError(
            name,
            f"Could not resolve work name '{name}'. "
            f"Try using the full TLG ID (e.g., tlg0059.tlg001) or check available aliases."
        )

    def _is_tlg_id(self, name: str) -> bool:
        """Check if name is already a TLG ID format."""
        # Format: tlg####.tlg###
        if "." not in name:
            return False
        parts = name.split(".")
        if len(parts) != 2:
            return False
        return parts[0].startswith("tlg") and parts[1].startswith("tlg")

    def _load_extracted_aliases(self):
        """Extract aliases from catalog (titles and common abbreviations)."""
        try:
            authors = self.catalog.list_authors()
            for author in authors:
                works = self.catalog.list_works(author.tlg_id)
                for work in works:
                    work_id = f"{work.tlg_id}.{work.work_id}"

                    # Add English title as alias (case-insensitive)
                    if work.title_en:
                        self.aliases[work.title_en.lower()] = work_id

                    # Add Greek title as alias
                    if work.title_grc:
                        self.aliases[work.title_grc.lower()] = work_id

        except Exception as e:
            logger.warning(f"Failed to extract aliases from catalog: {e}")

    def _load_config_file(self, config_path: Path):
        """Load aliases from YAML config file."""
        try:
            if not config_path.exists():
                return

            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if config and "aliases" in config:
                for alias, work_id in config["aliases"].items():
                    # Store as lowercase for case-insensitive lookup
                    self.aliases[alias.lower()] = work_id

        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_work_resolver.py -v`
Expected: `PASSED` (all tests)

**Step 5: Commit**

```bash
git add pi_grapheion/work_resolver.py tests/test_work_resolver.py
git commit -m "feat: add WorkResolver for work name and alias resolution"
```

---

## Task 2: Create Data Classes for Anthology

**Files:**
- Create: `pi_grapheion/anthology_extractor.py` (data classes only)
- Create: `tests/test_anthology_data.py`

**Step 1: Write the failing test**

Create `tests/test_anthology_data.py`:

```python
"""Tests for anthology data structures."""

import pytest
from pi_grapheion.anthology_extractor import PassageSpec, AnthologyBlock


def test_passage_spec_creation():
    """Test creating PassageSpec."""
    spec = PassageSpec(
        work_id="tlg0059.tlg001",
        ranges=["5a", "7b-c", "8"]
    )
    assert spec.work_id == "tlg0059.tlg001"
    assert spec.ranges == ["5a", "7b-c", "8"]


def test_anthology_block_creation():
    """Test creating AnthologyBlock."""
    block = AnthologyBlock(
        work_title_en="Euthyphro",
        work_title_gr="Εὐθύφρων",
        range_display="5a",
        segments=[{"text": "Sample", "stephanus": ["5a"]}],
        book=None
    )
    assert block.work_title_en == "Euthyphro"
    assert block.work_title_gr == "Εὐθύφρων"
    assert block.range_display == "5a"
    assert block.book is None


def test_anthology_block_format_header_no_book():
    """Test formatting header without book."""
    block = AnthologyBlock(
        work_title_en="Euthyphro",
        work_title_gr="Εὐθύφρων",
        range_display="5a",
        segments=[],
        book=None
    )
    header = block.format_header(width=79)

    assert "Euthyphro (Εὐθύφρων) 5a" in header
    assert "-" * 79 in header


def test_anthology_block_format_header_with_book():
    """Test formatting header with book number."""
    block = AnthologyBlock(
        work_title_en="Republic",
        work_title_gr="Πολιτεία",
        range_display="354b-c",
        segments=[],
        book="1"
    )
    header = block.format_header(width=79)

    # Should show "1.354b-c" format
    assert "Republic (Πολιτεία) 1.354b-c" in header
    assert "-" * 79 in header
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_anthology_data.py -v`
Expected: `ImportError` or `FAIL`

**Step 3: Write minimal implementation**

Create `pi_grapheion/anthology_extractor.py`:

```python
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
    range_display: str  # e.g., "5a" or "7b-c" or "1.354b-c"
    segments: List[Dict]
    book: Optional[str] = None

    def format_header(self, width: int = 79) -> str:
        """
        Format the header for this anthology block.

        Returns:
            Formatted header with title, range, and separator line
        """
        # Format range with book if present
        if self.book:
            range_str = f"{self.book}.{self.range_display}"
        else:
            range_str = self.range_display

        # Create header line
        header_line = f"{self.work_title_en} ({self.work_title_gr}) {range_str}"
        separator = "-" * width

        return f"\n{header_line}\n{separator}\n"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_anthology_data.py -v`
Expected: `PASSED`

**Step 5: Commit**

```bash
git add pi_grapheion/anthology_extractor.py tests/test_anthology_data.py
git commit -m "feat: add data classes for anthology extraction"
```

---

## Task 3: Implement Range List Parsing

**Files:**
- Modify: `pi_grapheion/anthology_extractor.py`
- Modify: `tests/test_anthology_data.py`

**Step 1: Write the failing test**

Add to `tests/test_anthology_data.py`:

```python
from pi_grapheion.anthology_extractor import parse_passage_ranges


class TestPassageRangeParsing:
    """Tests for parsing comma-separated range lists."""

    def test_parse_simple_ranges(self):
        """Test parsing simple comma-separated ranges."""
        ranges = parse_passage_ranges("5a,7b-c,8")
        assert ranges == ["5a", "7b-c", "8"]

    def test_parse_ranges_with_spaces(self):
        """Test parsing ranges with spaces around commas."""
        ranges = parse_passage_ranges("5a, 7b-c, 8")
        assert ranges == ["5a", "7b-c", "8"]

    def test_parse_single_range(self):
        """Test parsing single range."""
        ranges = parse_passage_ranges("5a")
        assert ranges == ["5a"]

    def test_parse_invalid_range_raises_error(self):
        """Test that invalid range format raises ValueError."""
        with pytest.raises(ValueError):
            parse_passage_ranges("abc-xyz-123")

    def test_parse_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            parse_passage_ranges("")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_anthology_data.py::TestPassageRangeParsing -v`
Expected: `ImportError` or `FAIL`

**Step 3: Write minimal implementation**

Add to `pi_grapheion/anthology_extractor.py`:

```python
from pi_grapheion.range_filter import StephanusRangeParser


def parse_passage_ranges(range_string: str) -> List[str]:
    """
    Parse comma-separated range list into individual ranges.

    Args:
        range_string: Comma-separated ranges (e.g., "5a, 7b-c, 8")

    Returns:
        List of range strings

    Raises:
        ValueError: If any range is invalid
    """
    if not range_string or not range_string.strip():
        raise ValueError("Empty range specification")

    # Split on comma and strip whitespace
    ranges = [r.strip() for r in range_string.split(",")]

    # Validate each range
    parser = StephanusRangeParser()
    for r in ranges:
        parser.parse(r)  # Raises ValueError if invalid

    return ranges
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_anthology_data.py::TestPassageRangeParsing -v`
Expected: `PASSED`

**Step 5: Commit**

```bash
git add pi_grapheion/anthology_extractor.py tests/test_anthology_data.py
git commit -m "feat: add range list parsing for anthology"
```

---

## Task 4: Implement AnthologyExtractor Core Logic

**Files:**
- Modify: `pi_grapheion/anthology_extractor.py`
- Create: `tests/test_anthology_extractor.py`

**Step 1: Write the failing test**

Create `tests/test_anthology_extractor.py`:

```python
"""Tests for AnthologyExtractor."""

import pytest
from pathlib import Path
from pi_grapheion.anthology_extractor import AnthologyExtractor, PassageSpec


class TestAnthologyExtractor:
    """Tests for extracting anthology blocks."""

    def test_extract_single_work_single_range(self):
        """Test extracting single range from single work."""
        specs = [
            PassageSpec(work_id="tlg0059.tlg001", ranges=["2a"])
        ]

        extractor = AnthologyExtractor()
        blocks = extractor.extract_anthology(specs)

        assert len(blocks) == 1
        assert blocks[0].work_title_en == "Euthyphro"
        assert blocks[0].range_display == "2a"
        assert len(blocks[0].segments) > 0

    def test_extract_single_work_multiple_ranges(self):
        """Test extracting multiple discontinuous ranges from single work."""
        specs = [
            PassageSpec(work_id="tlg0059.tlg001", ranges=["2a", "3b-c"])
        ]

        extractor = AnthologyExtractor()
        blocks = extractor.extract_anthology(specs)

        # Should produce 2 blocks (one per range)
        assert len(blocks) == 2
        assert blocks[0].range_display == "2a"
        assert blocks[1].range_display == "3b-c"

    def test_extract_multiple_works(self):
        """Test extracting from multiple works."""
        specs = [
            PassageSpec(work_id="tlg0059.tlg001", ranges=["2a"]),
            PassageSpec(work_id="tlg0059.tlg004", ranges=["59a"])
        ]

        extractor = AnthologyExtractor()
        blocks = extractor.extract_anthology(specs)

        # Should produce 2 blocks (one per work)
        assert len(blocks) == 2
        assert blocks[0].work_title_en == "Euthyphro"
        assert blocks[1].work_title_en == "Phaedo"

    def test_detect_book_in_multibook_work(self):
        """Test that book numbers are detected for multi-book works."""
        # Republic Book 1
        specs = [
            PassageSpec(work_id="tlg0059.tlg030", ranges=["327a"])
        ]

        extractor = AnthologyExtractor()
        blocks = extractor.extract_anthology(specs)

        assert len(blocks) == 1
        # Should detect book number
        assert blocks[0].book == "1"

    def test_extract_with_invalid_work_raises_error(self):
        """Test that invalid work ID raises error."""
        specs = [
            PassageSpec(work_id="tlg9999.tlg999", ranges=["1a"])
        ]

        extractor = AnthologyExtractor()
        with pytest.raises(Exception):  # Could be WorkNotFoundError
            extractor.extract_anthology(specs)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_anthology_extractor.py -v`
Expected: `ImportError` or `FAIL`

**Step 3: Write minimal implementation**

Add to `pi_grapheion/anthology_extractor.py`:

```python
from pi_grapheion.parser import TEIParser
from pi_grapheion.extractor import TextExtractor
from pi_grapheion.catalog import PerseusCatalog
from pi_grapheion.range_filter import RangeFilter
from pi_grapheion.exceptions import WorkNotFoundError


class AnthologyExtractor:
    """Extract anthology blocks from multiple works and ranges."""

    def __init__(self):
        self.catalog = PerseusCatalog()
        self.range_filter = RangeFilter()

    def extract_anthology(self, specs: List[PassageSpec]) -> List[AnthologyBlock]:
        """
        Extract anthology blocks from passage specifications.

        Args:
            specs: List of PassageSpec objects

        Returns:
            List of AnthologyBlock objects

        Raises:
            WorkNotFoundError: If work cannot be found
        """
        blocks = []

        for spec in specs:
            # Resolve work ID to file path
            work_file = self.catalog.resolve_work_id(spec.work_id)

            # Get work metadata
            work_metadata = self._get_work_metadata(spec.work_id)

            # Parse and extract text
            parser = TEIParser(work_file)
            extractor = TextExtractor(parser)
            dialogue = extractor.get_dialogue_text()

            # Extract each range as separate block
            for range_spec in spec.ranges:
                # Filter to range
                filtered_segments = self.range_filter.filter(
                    dialogue, range_spec, work_id=spec.work_id
                )

                # Detect book number if present
                book_num = self._detect_book_number(filtered_segments)

                # Create anthology block
                block = AnthologyBlock(
                    work_title_en=work_metadata["title_en"],
                    work_title_gr=work_metadata["title_gr"],
                    range_display=range_spec,
                    segments=filtered_segments,
                    book=book_num
                )
                blocks.append(block)

        return blocks

    def _get_work_metadata(self, work_id: str) -> Dict:
        """Get work metadata (titles) from catalog."""
        # Split work_id: tlg####.tlg###
        parts = work_id.split(".")
        author_id = parts[0]

        works = self.catalog.list_works(author_id)
        for work in works:
            if f"{work.tlg_id}.{work.work_id}" == work_id:
                return {
                    "title_en": work.title_en,
                    "title_gr": work.title_grc or work.title_en
                }

        raise WorkNotFoundError(work_id, f"Could not find metadata for {work_id}")

    def _detect_book_number(self, segments: List[Dict]) -> Optional[str]:
        """
        Detect book number from segments if present.

        Args:
            segments: List of dialogue segments

        Returns:
            Book number string or None
        """
        # Check if any segment has a book field
        for segment in segments:
            if "book" in segment and segment["book"]:
                return segment["book"]
        return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_anthology_extractor.py -v`
Expected: `PASSED` (or `SKIP` if Perseus files not available)

**Step 5: Commit**

```bash
git add pi_grapheion/anthology_extractor.py tests/test_anthology_extractor.py
git commit -m "feat: implement AnthologyExtractor core logic"
```

---

## Task 5: Create AnthologyFormatter

**Files:**
- Create: `pi_grapheion/anthology_formatter.py`
- Create: `tests/test_anthology_formatter.py`

**Step 1: Write the failing test**

Create `tests/test_anthology_formatter.py`:

```python
"""Tests for AnthologyFormatter."""

import pytest
from pi_grapheion.anthology_formatter import AnthologyFormatter
from pi_grapheion.anthology_extractor import AnthologyBlock
from pi_grapheion.formatter import OutputStyle


class TestAnthologyFormatter:
    """Tests for formatting anthology output."""

    def test_format_single_block(self):
        """Test formatting single anthology block."""
        block = AnthologyBlock(
            work_title_en="Euthyphro",
            work_title_gr="Εὐθύφρων",
            range_display="5a",
            segments=[
                {"speaker": "Σωκράτης", "label": "ΣΩ.", "text": "Sample text", "stephanus": ["5a"]}
            ],
            book=None
        )

        formatter = AnthologyFormatter()
        result = formatter.format([block], OutputStyle.FULL_MODERN)

        # Should contain header
        assert "Euthyphro (Εὐθύφρων) 5a" in result
        assert "-" * 79 in result
        # Should contain text
        assert "Sample text" in result

    def test_format_multiple_blocks_separated(self):
        """Test multiple blocks are separated by blank lines."""
        blocks = [
            AnthologyBlock(
                work_title_en="Euthyphro",
                work_title_gr="Εὐθύφρων",
                range_display="5a",
                segments=[{"text": "Text 1", "stephanus": ["5a"]}],
                book=None
            ),
            AnthologyBlock(
                work_title_en="Euthyphro",
                work_title_gr="Εὐθύφρων",
                range_display="7b",
                segments=[{"text": "Text 2", "stephanus": ["7b"]}],
                book=None
            )
        ]

        formatter = AnthologyFormatter()
        result = formatter.format(blocks, OutputStyle.FULL_MODERN)

        # Should have both headers
        assert "Euthyphro (Εὐθύφρων) 5a" in result
        assert "Euthyphro (Εὐθύφρων) 7b" in result
        # Should have blank line separator between blocks
        assert "\n\n" in result

    def test_format_with_book_number(self):
        """Test formatting block with book number."""
        block = AnthologyBlock(
            work_title_en="Republic",
            work_title_gr="Πολιτεία",
            range_display="354b",
            segments=[{"text": "Text", "stephanus": ["354b"]}],
            book="1"
        )

        formatter = AnthologyFormatter()
        result = formatter.format([block], OutputStyle.FULL_MODERN)

        # Header should show "1.354b" format
        assert "Republic (Πολιτεία) 1.354b" in result

    def test_format_respects_output_style(self):
        """Test that output style is applied to text."""
        block = AnthologyBlock(
            work_title_en="Euthyphro",
            work_title_gr="Εὐθύφρων",
            range_display="5a",
            segments=[
                {"speaker": "Σωκράτης", "label": "ΣΩ.", "text": "Τί νεόν;", "stephanus": ["5a"]}
            ],
            book=None
        )

        formatter = AnthologyFormatter()

        # Style A should work
        result_a = formatter.format([block], OutputStyle.FULL_MODERN)
        assert len(result_a) > 0

        # Style C should work
        result_c = formatter.format([block], OutputStyle.NO_PUNCTUATION)
        assert len(result_c) > 0

    def test_format_rejects_style_e(self):
        """Test that style E (scriptio continua) raises error."""
        block = AnthologyBlock(
            work_title_en="Euthyphro",
            work_title_gr="Εὐθύφρων",
            range_display="5a",
            segments=[{"text": "Text", "stephanus": ["5a"]}],
            book=None
        )

        formatter = AnthologyFormatter()
        with pytest.raises(InvalidStyleError) as exc_info:
            formatter.format([block], OutputStyle.SCRIPTIO_CONTINUA)

        assert "styles A-D" in str(exc_info.value).lower()

    def test_format_rejects_style_s(self):
        """Test that style S (Stephanus layout) raises error."""
        block = AnthologyBlock(
            work_title_en="Euthyphro",
            work_title_gr="Εὐθύφρων",
            range_display="5a",
            segments=[{"text": "Text", "stephanus": ["5a"]}],
            book=None
        )

        formatter = AnthologyFormatter()
        with pytest.raises(InvalidStyleError) as exc_info:
            formatter.format([block], OutputStyle.STEPHANUS_LAYOUT)

        assert "styles A-D" in str(exc_info.value).lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_anthology_formatter.py -v`
Expected: `ImportError` or `FAIL`

**Step 3: Write minimal implementation**

Create `pi_grapheion/anthology_formatter.py`:

```python
"""Formatter for anthology output with headers and blocks."""

from typing import List
from pi_grapheion.anthology_extractor import AnthologyBlock
from pi_grapheion.formatter import TextFormatter, OutputStyle
from pi_grapheion.exceptions import InvalidStyleError


class AnthologyFormatter:
    """Format anthology blocks with headers and proper separation."""

    # Styles allowed for anthology output
    ALLOWED_STYLES = {
        OutputStyle.FULL_MODERN,
        OutputStyle.MINIMAL_PUNCTUATION,
        OutputStyle.NO_PUNCTUATION,
        OutputStyle.NO_PUNCTUATION_NO_LABELS,
    }

    def format(self, blocks: List[AnthologyBlock], style: OutputStyle) -> str:
        """
        Format anthology blocks into final output.

        Args:
            blocks: List of AnthologyBlock objects
            style: Output style to apply (A-D only)

        Returns:
            Formatted anthology text with headers

        Raises:
            InvalidStyleError: If style E or S is used
        """
        # Validate style
        if style not in self.ALLOWED_STYLES:
            raise InvalidStyleError(
                style.value,
                "Anthology extraction only supports styles A-D. "
                "Styles E (scriptio continua) and S (Stephanus layout) are not "
                "compatible with multi-passage anthology format."
            )

        output_parts = []

        for block in blocks:
            # Add header for this block
            header = block.format_header(width=79)
            output_parts.append(header)

            # Format the text content using TextFormatter
            formatter = TextFormatter(block.segments)
            formatted_text = formatter.format(style)
            output_parts.append(formatted_text)

            # Add blank line separator after block (except last)
            if block != blocks[-1]:
                output_parts.append("\n")

        return "".join(output_parts)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_anthology_formatter.py -v`
Expected: `PASSED`

**Step 5: Commit**

```bash
git add pi_grapheion/anthology_formatter.py tests/test_anthology_formatter.py
git commit -m "feat: implement AnthologyFormatter for block output"
```

---

## Task 6: Integrate Anthology into CLI

**Files:**
- Modify: `pi_grapheion/cli.py`
- Create: `tests/test_cli_anthology.py`

**Step 1: Write the failing test**

Create `tests/test_cli_anthology.py`:

```python
"""Integration tests for CLI anthology extraction."""

import pytest
from pathlib import Path
from pi_grapheion.cli import main
import sys


def test_cli_single_work_multiple_passages(monkeypatch, capsys):
    """Test extracting multiple passages from single work."""
    xml_path = Path("tests/fixtures/sample_minimal.xml")
    if not xml_path.exists():
        pytest.skip("Sample XML not found")

    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        str(xml_path),
        '--passages', '2a,3b',
        '--print'
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    # Should contain headers for both passages
    assert "2a" in captured.out
    assert "3b" in captured.out or "sample" in captured.out.lower()


def test_cli_multiple_works_with_passages(monkeypatch, capsys):
    """Test extracting passages from multiple works."""
    # Skip if Perseus not available
    euth_path = Path("canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc2.xml")
    if not euth_path.exists():
        pytest.skip("Perseus files not available")

    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        'euthyphro', '--passages', '2a',
        'phaedo', '--passages', '59a',
        '--print'
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    # Should contain both work titles
    assert "Euthyphro" in captured.out or "Εὐθύφρων" in captured.out
    assert "Phaedo" in captured.out or "Φαίδων" in captured.out


def test_cli_work_resolution_by_name(monkeypatch, capsys):
    """Test that work names are resolved to TLG IDs."""
    euth_path = Path("canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc2.xml")
    if not euth_path.exists():
        pytest.skip("Perseus files not available")

    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        'euthyphro',  # Use name instead of TLG ID
        '--passages', '2a',
        '--print'
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    assert len(captured.out) > 0


def test_cli_anthology_with_output_file(monkeypatch, tmp_path):
    """Test anthology output to file."""
    xml_path = Path("tests/fixtures/sample_minimal.xml")
    if not xml_path.exists():
        pytest.skip("Sample XML not found")

    output_file = tmp_path / "anthology.txt"

    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        str(xml_path),
        '--passages', '2a',
        '--output', str(output_file)
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    # Check file was created
    assert output_file.exists()
    content = output_file.read_text()
    assert len(content) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_anthology.py -v`
Expected: `FAIL` (CLI doesn't support --passages yet)

**Step 3: Write minimal implementation**

Modify `pi_grapheion/cli.py`:

1. Add imports:
```python
from pi_grapheion.work_resolver import WorkResolver
from pi_grapheion.anthology_extractor import AnthologyExtractor, PassageSpec, parse_passage_ranges
from pi_grapheion.anthology_formatter import AnthologyFormatter
```

2. Create new `handle_extract_anthology` function:
```python
def handle_extract_anthology(args):
    """Handle anthology extraction with --passages flag."""
    # Parse work/passages pairs
    specs = []
    resolver = WorkResolver()

    # args.works is list of (work_name, passages_string) tuples
    for work_name, passages_str in args.works:
        # Resolve work name to TLG ID
        try:
            work_id = resolver.resolve(work_name)
        except WorkNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Parse passage ranges
        try:
            ranges = parse_passage_ranges(passages_str)
        except ValueError as e:
            print(f"Error parsing ranges '{passages_str}': {e}", file=sys.stderr)
            sys.exit(1)

        specs.append(PassageSpec(work_id=work_id, ranges=ranges))

    # Determine output style
    style_map = {
        "A": OutputStyle.FULL_MODERN,
        "B": OutputStyle.MINIMAL_PUNCTUATION,
        "C": OutputStyle.NO_PUNCTUATION,
        "D": OutputStyle.NO_PUNCTUATION_NO_LABELS,
        "E": OutputStyle.SCRIPTIO_CONTINUA,
        "S": OutputStyle.STEPHANUS_LAYOUT,
    }
    output_style = style_map.get(args.style, OutputStyle.FULL_MODERN)

    # Extract anthology
    try:
        extractor = AnthologyExtractor()
        blocks = extractor.extract_anthology(specs)

        # Format output
        formatter = AnthologyFormatter()
        formatted_text = formatter.format(blocks, output_style)

        # Output
        if args.print or (args.output and str(args.output) == "-"):
            print(formatted_text)
        elif args.output:
            args.output.write_text(formatted_text, encoding="utf-8")
            print(f"Successfully created: {args.output}")
        else:
            # Default output to file
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"anthology_{args.style}.txt"
            output_file.write_text(formatted_text, encoding="utf-8")
            print(f"Successfully created: {output_file}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
```

3. Modify argument parser to support new syntax:
```python
# In the extract_parser setup section
extract_parser.add_argument(
    "works_and_passages",
    nargs="*",
    help="Work names/IDs optionally followed by --passages"
)
extract_parser.add_argument(
    "--passages",
    action="append",
    dest="passage_list",
    help="Comma-separated passage ranges for preceding work"
)

# In main(), add logic to parse work/passage pairs
def parse_work_passages(args):
    """Parse alternating work names and --passages flags."""
    works = []
    current_work = None

    # Check if --passages was used
    if hasattr(args, 'passage_list') and args.passage_list:
        # New anthology mode
        # Parse: work1 --passages ranges1 work2 --passages ranges2
        i = 0
        work_passages = []
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg not in ['--passages', '-p'] and not arg.startswith('-'):
                # This is a work name
                current_work = arg
            elif arg in ['--passages', '-p']:
                # Next arg is passage ranges
                if i + 1 < len(sys.argv) and current_work:
                    passages = sys.argv[i + 1]
                    work_passages.append((current_work, passages))
                    i += 1  # Skip the passages arg
            i += 1

        args.works = work_passages
        return True
    return False

# Update the command routing
if parse_work_passages(args):
    handle_extract_anthology(args)
else:
    handle_extract(args)  # Existing single-work extraction
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_anthology.py -v`
Expected: `PASSED` (or `SKIP` for tests requiring Perseus)

**Step 5: Commit**

```bash
git add pi_grapheion/cli.py tests/test_cli_anthology.py
git commit -m "feat: integrate anthology extraction into CLI"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `README.md`
- Create: `.pi-grapheion/aliases.yaml.example`

**Step 1: Add anthology examples to README**

Add new section after "Extracting Specific Ranges":

```markdown
#### Extracting Anthology (Discontinuous Passages)

Extract multiple discontinuous passages within or across works:

```bash
# Multiple passages from single work
python -m pi_grapheion.cli extract euthyphro --passages 5a,7b-c,8 --print

# Passages from multiple works
python -m pi_grapheion.cli extract \
  euthyphro --passages 2a,3b \
  phaedo --passages 59a \
  republic --passages 327a-b \
  --print

# Using work aliases
python -m pi_grapheion.cli extract republic --passages 354b-c,357a --print
```

**Output Format:**
Each passage is displayed as a separate block with contextual header:

```
Euthyphro (Εὐθύφρων) 5a
-------------------------------------------------------------------------------
[Text of section 5a]

Euthyphro (Εὐθύφρων) 7b-c
-------------------------------------------------------------------------------
[Text of sections 7b-c]

Phaedo (Φαίδων) 59a
-------------------------------------------------------------------------------
[Text of section 59a]
```

**Work Name Resolution:**
- Use full TLG IDs: `tlg0059.tlg001`
- Use English titles: `euthyphro`, `republic`, `phaedo`
- Use Greek titles: `Εὐθύφρων`, `Πολιτεία`
- Case-insensitive: `Euthyphro`, `euthyphro`, `EUTHYPHRO` all work

**Custom Aliases:**
Define shortcuts in config files:

User config (`~/.pi-grapheion/aliases.yaml`):
```yaml
aliases:
  euth: tlg0059.tlg001
  rep: tlg0059.tlg030
  symp: tlg0059.tlg011
```

Project config (`.pi-grapheion/aliases.yaml`):
```yaml
aliases:
  mywork: tlg0059.tlg001
```

Project config overrides user config for conflicting aliases.
```

**Step 2: Create example config file**

Create `.pi-grapheion/aliases.yaml.example`:

```yaml
# User-defined work aliases for pi-grapheion
#
# Copy this file to:
#   - ~/.pi-grapheion/aliases.yaml (user-level)
#   - .pi-grapheion/aliases.yaml (project-level)
#
# Project-level aliases override user-level aliases.

aliases:
  # Common abbreviations
  euth: tlg0059.tlg001  # Plato's Euthyphro
  rep: tlg0059.tlg030   # Plato's Republic
  symp: tlg0059.tlg011  # Plato's Symposium
  phaedo: tlg0059.tlg004  # Plato's Phaedo

  # Custom shortcuts
  # mytext: tlg####.tlg###
```

**Step 3: Update features list**

Update the features section:

```markdown
## Features

- **Catalog browsing** - List authors, search works, resolve work IDs
- **Range extraction** - Extract specific Stephanus passages (e.g., `2a`, `2-5`, `2a-3e`)
- **Anthology extraction** - Combine discontinuous passages from multiple works
- **Work name aliases** - Use `euthyphro` instead of `tlg0059.tlg001`
- **Six output styles** (A-E, S) from modern to ancient formatting
...
```

**Step 4: Commit**

```bash
git add README.md .pi-grapheion/aliases.yaml.example
git commit -m "docs: add anthology extraction and aliases to README"
```

---

## Task 8: Run Full Test Suite and Verification

**Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests pass (some may skip if Perseus files unavailable)

**Step 2: Manual testing**

Test the full workflow:

```bash
# Test work resolution
python -m pi_grapheion.cli extract euthyphro --passages 2a --print

# Test multiple passages
python -m pi_grapheion.cli extract euthyphro --passages "2a, 3b" --print

# Test multiple works (if Perseus available)
python -m pi_grapheion.cli extract \
  euthyphro --passages 2a \
  phaedo --passages 59a \
  --print

# Test with different styles
python -m pi_grapheion.cli extract euthyphro --passages 2a-3b --style C --print

# Test output to file
python -m pi_grapheion.cli extract euthyphro --passages 2a --output test_anthology.txt
```

**Step 3: Verify examples in README**

Run each example from README to ensure they work.

**Step 4: Check git status**

```bash
git log --oneline
git status
```

Expected: Clean working directory, ~8-10 commits

---

## Implementation Complete

**Feature Summary:**
- ✅ Work name resolution with aliases (extracted + user-defined)
- ✅ Anthology extraction for discontinuous passages
- ✅ Support for single-work and multi-work anthologies
- ✅ Contextual headers with English and Greek titles
- ✅ Book number detection for multi-book works
- ✅ Integration with styles A-D (E and S raise clear errors)
- ✅ Config file support (user + project)
- ✅ Comprehensive test coverage
- ✅ Updated documentation

**New Components:**
- `work_resolver.py` - Alias resolution system
- `anthology_extractor.py` - Multi-passage extraction
- `anthology_formatter.py` - Block formatting
- Config system - `~/.pi-grapheion/aliases.yaml` and `.pi-grapheion/aliases.yaml`

**CLI Syntax:**
```bash
extract work1 --passages ranges1 [work2 --passages ranges2 ...] [options]
```

**Testing Checklist:**
- Unit tests for WorkResolver (alias lookup, config loading)
- Unit tests for range parsing and validation
- Unit tests for AnthologyExtractor (single/multi work)
- Unit tests for AnthologyFormatter (headers, separation)
- Integration tests for CLI
- Manual testing with real Perseus files
