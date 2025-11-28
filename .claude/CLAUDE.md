# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Purpose

**π-grapheion** (pi-grapheion) - A Python tool for extracting and reformatting Greek texts from TEI XML files in the Perseus Digital Library. The name comes from γραφεῖον (grapheion), the ancient Greek writing tablet. Generates plain text versions in various styles (modern edition to ancient scriptio continua).

## Quick Start

```bash
# List available texts
.venv/bin/python -m pi_grapheion.cli list-authors
.venv/bin/python -m pi_grapheion.cli search "Plato"

# Extract text by work name or ID
.venv/bin/python -m pi_grapheion.cli extract euthyphro --style A
.venv/bin/python -m pi_grapheion.cli extract tlg0059.tlg001 --style A

# Extract specific range
.venv/bin/python -m pi_grapheion.cli extract euthyphro 2a-5e --print

# Run tests
.venv/bin/python -m pytest tests/ -v
```

## Architecture

**Pipeline**: XML → TEIParser → TextExtractor → TextFormatter → Output

**Core modules**:
- `parser.py` - Parses TEI XML, validates structure, extracts metadata
- `extractor.py` - Extracts text from `<said>` elements, handles Stephanus markers
- `formatter.py` - Applies output styles (A-E, S)
- `catalog.py` - Browses/searches Perseus catalog (99 authors, 818 works)
- `work_resolver.py` - Resolves work name aliases to TLG IDs
- `anthology_extractor.py` - Extracts multiple passages from one or more works
- `anthology_formatter.py` - Formats anthology blocks with headers
- `range_filter.py` - Filters segments by Stephanus ranges
- `cli.py` - Command-line interface with subcommands and anthology mode
- `exceptions.py` - Custom exceptions (WorkNotFoundError, InvalidTEIStructureError, EmptyExtractionError, InvalidStephanusRangeError)

**Data flow**:
```python
# Extracted data structure (each segment)
{
    "speaker": "Σωκράτης",
    "label": "ΣΩ.",
    "text": "κατέβην χθὲς...",
    "stephanus": ["327", "327a"],
    "said_id": 0,
    "is_paragraph_start": False,
    "book": "1"  # For multi-book works
}
```

## Key Features

### Output Styles
- **A (FULL_MODERN)**: All punctuation + labels + Stephanus markers (default)
- **B (MINIMAL_PUNCTUATION)**: Periods and question marks only
- **C (NO_PUNCTUATION)**: Preserves labels and spacing
- **D (NO_PUNCTUATION_NO_LABELS)**: Continuous text
- **E (SCRIPTIO_CONTINUA)**: Ancient style - uppercase, no spaces/punctuation
- **S (STEPHANUS_LAYOUT)**: 1578 edition style - 40-char columns with margin markers
  - ⚠️ **Only valid for Plato's works (tlg0059)** - raises `InvalidStyleError` otherwise

### Multi-Book Works
- Titles: UPPERCASE WITHOUT ACCENTS (e.g., ΠΟΛΙΤΕΙΑ)
- Book headers: "TITLE NUMERAL" (e.g., ΠΟΛΙΤΕΙΑ Α)
- Automatic detection via `<div type="textpart" subtype="book">`

### Catalog Browsing
```bash
.venv/bin/python -m pi_grapheion.cli list-authors              # All 99 authors
.venv/bin/python -m pi_grapheion.cli list-works Plato          # By author name (case-insensitive)
.venv/bin/python -m pi_grapheion.cli list-works tlg0059        # Or by TLG ID
.venv/bin/python -m pi_grapheion.cli list-works --all          # All 818 works
.venv/bin/python -m pi_grapheion.cli search "Republic"         # Search by title/author
```

**Note**: `list-works` output now includes page/section ranges for each work:
- Plato: Stephanus page numbers (e.g., `[2-16]`, `[327-621]`)
- Plutarch: Stephanus page numbers (e.g., `[1012-1030]`)
- Isocrates and others: Section numbers (e.g., `[1-58]`)

### Anthology Extraction (NEW)
Extract discontinuous passages from one or more works using work name aliases:

```bash
# Single work, multiple ranges
.venv/bin/python -m pi_grapheion.cli extract euthyphro --passages 5a,7b-7c,10a

# Multiple works
.venv/bin/python -m pi_grapheion.cli extract euthyphro --passages 5a republic --passages 354b

# Using TLG IDs
.venv/bin/python -m pi_grapheion.cli extract tlg0059.tlg001 --passages 2a,3b tlg0059.tlg030 --passages 327a
```

**Features**:
- Work name aliases: Use "euthyphro" instead of "tlg0059.tlg001"
- Discontinuous ranges: Extract non-contiguous passages (e.g., "5a, 7b-7c, 10a")
- Multi-work extraction: Combine passages from different works
- Contextual headers: Each block shows work title (Greek + English) and range
- Style restriction: Only A-D supported (E and S raise `InvalidStyleError`)

**Alias Configuration**:
- User config: `~/.pi-grapheion/aliases.yaml`
- Project config: `.pi-grapheion/aliases.yaml` (overrides user)
- Automatic from catalog (English/Greek titles)
- Case-insensitive matching

### Logging & Debugging
```bash
# Normal mode: warnings only
.venv/bin/python -m pi_grapheion.cli extract tlg0059.tlg001

# Debug mode: full tracebacks and metadata parsing issues
.venv/bin/python -m pi_grapheion.cli --debug extract tlg0059.tlg001
```

## TEI XML Structure

Perseus texts use TEI P5:
- Namespace: `http://www.tei-c.org/ns/1.0`
- Dialogue: `<said who="#Speaker">` with `<label>` abbreviations
- Stephanus pagination (Plato): `<milestone n="327a" unit="section"/>`
- Stephanus pagination (Plutarch): `<milestone n="1012b" unit="stephpage"/>`
- Section numbering (Isocrates, others): `<div type="textpart" subtype="section" n="1">`
- Paragraph breaks: `<milestone ed="P" unit="para"/>`
- Books: `<div type="textpart" subtype="book" n="1">`

**Note**: The extractor automatically detects both milestone-based pagination (Plato, Plutarch) and div-based section numbering (Isocrates, other authors). Both appear in the `stephanus` field and are formatted identically in output.

## Development Guidelines

### Testing (TDD)
```bash
# Write test first, then implementation
.venv/bin/python -m pytest tests/test_module.py -v
.venv/bin/python -m pytest tests/ --cov=src
```

### Code Quality
```bash
.venv/bin/python -m black src tests
.venv/bin/python -m ruff check src tests
```

### Critical Warnings
- ⚠️ **NEVER read entire `canonical-greekLit/data` directory** - too large (~100 authors, 818 works)
- ⚠️ **Never write to canonical-greekLit directory** - CLI warns if attempted
- ✅ Output goes to `./output/` by default

## Common Tasks

### Extract by Work Name or ID (recommended)
```bash
# 1. Search for work
.venv/bin/python -m pi_grapheion.cli search "Phaedo"

# 2. Extract by work name alias (case-insensitive)
.venv/bin/python -m pi_grapheion.cli extract phaedo --style A

# 3. Or extract by TLG work ID
.venv/bin/python -m pi_grapheion.cli extract tlg0059.tlg004 --style A

# 4. Extract specific range with alias
.venv/bin/python -m pi_grapheion.cli extract phaedo 59a-60b --print
```

### Extract by File Path (backward compatible)
```bash
.venv/bin/python -m pi_grapheion.cli extract canonical-greekLit/data/tlg0059/tlg004/tlg0059.tlg004.perseus-grc2.xml
```

### Custom Exceptions
The tool provides helpful error messages:
- `WorkNotFoundError` - Invalid work ID, with suggestions
- `InvalidTEIStructureError` - Missing required TEI elements
- `EmptyExtractionError` - No text extracted from file
- `InvalidStyleError` - Style used inappropriately (e.g., Style S on non-Platonic works)

## Special Cases

### Pagination and Section Markers
- **Stephanus markers (Plato)**: `<milestone unit="section">` - some lack `resp="Stephanus"` attribute
- **Stephanus markers (Plutarch)**: `<milestone unit="stephpage">` for Moralia works
- **Section numbers (Isocrates, others)**: `<div subtype="section">` with numeric `n` attribute
- Markers split at boundaries to ensure correct placement in output
- Editorial paragraph breaks preserved via `is_paragraph_start` flag
- The extractor's `_find_section_number()` method traverses the element tree to detect section divs

### Accent Removal
Greek titles/headers in uppercase use Unicode NFD normalization to strip accents (standard epigraphic convention).

### Work ID Format
- Format: `tlg####.tlg###` (e.g., `tlg0059.tlg001`)
- First part: author TLG ID
- Second part: work ID
- Both must start with "tlg"
