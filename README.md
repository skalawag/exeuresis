# π-grapheion

A Python tool for extracting and reformatting ancient Greek texts from the Perseus Digital Library.

## Overview

This tool extracts text from TEI XML files from the Perseus Digital Library and outputs them in various formats, from fully modern editions with punctuation and apparatus to ancient Greek scriptio continua. It includes a comprehensive catalog browser for discovering and accessing the 818 works from 99 ancient Greek authors in the Perseus corpus.

## Features

- **Catalog browsing** - List authors, search works, resolve work IDs
- **Range extraction** - Extract specific Stephanus passages (e.g., `2a`, `2-5`, `2a-3e`)
- **Six output styles** (A-E, S) from modern to ancient formatting
- **Multi-book work support** - Handles works like Plato's Republic with automatic book headers
- **Stephanus pagination** - Preserves classical reference system for Plato
- **Speaker label extraction** - Automatic detection for dialogue works
- **Comprehensive error handling** - Clear, actionable error messages
- **Command-line interface** - Intuitive subcommands for all operations
- **Test coverage: 64%** - 73 tests with TDD methodology

## Installation

```bash
# Clone this repository
git clone <repository-url>
cd pi-grapheion

# Clone the Perseus Digital Library corpus (MUST be at project root)
git clone https://github.com/PerseusDL/canonical-greekLit.git

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows

# Install with development dependencies
pip install -e ".[dev]"
```

**Important**:
- The `canonical-greekLit` directory **must** be located at the project root (same level as `pi_grapheion/`)
- It contains ~99 authors and 818 works (several hundred MB of data)
- The tool expects to find it at `./canonical-greekLit/data/`

## Quick Start

```bash
# Browse the catalog
python -m pi_grapheion.cli list-authors
python -m pi_grapheion.cli search "Plato"
python -m pi_grapheion.cli list-works tlg0059

# Extract text by work ID (recommended)
python -m pi_grapheion.cli extract tlg0059.tlg001 --style A

# Or by file path
python -m pi_grapheion.cli extract canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml
```

## Usage

### Catalog Commands

#### List Authors
```bash
# List all 99 authors
python -m pi_grapheion.cli list-authors

# Output format: TLG ID, English name, Greek name
# tlg0059: Plato (Πλάτων)
```

#### Search Works
```bash
# Search by title or author name (case-insensitive)
python -m pi_grapheion.cli search "Euthyphro"
python -m pi_grapheion.cli search "Plato"
python -m pi_grapheion.cli search "Φαίδων"  # Greek text supported

# Results show: Author TLG ID, Work ID, Title
```

#### List Works
```bash
# List works by specific author
python -m pi_grapheion.cli list-works tlg0059  # Plato's 36 works

# List all 818 works from all authors
python -m pi_grapheion.cli list-works --all
```

### Extract Text

#### By Work ID (Recommended)
```bash
# Format: tlg####.tlg### (author.work)
python -m pi_grapheion.cli extract tlg0059.tlg001  # Plato's Euthyphro
python -m pi_grapheion.cli extract tlg0059.tlg030  # Plato's Republic

# Specify output style
python -m pi_grapheion.cli extract tlg0059.tlg001 --style A
python -m pi_grapheion.cli extract tlg0059.tlg001 --style E

# Specify output file
python -m pi_grapheion.cli extract tlg0059.tlg001 --output euthyphro.txt

# Print to console
python -m pi_grapheion.cli extract tlg0059.tlg001 --print
```

#### By File Path
```bash
# Backward compatible with direct file paths
python -m pi_grapheion.cli extract canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml
```

#### Extracting Specific Ranges

Extract specific Stephanus passages instead of entire works:

```bash
# Single section
python -m pi_grapheion.cli extract tlg0059.tlg001 2a

# Single page (all sections)
python -m pi_grapheion.cli extract tlg0059.tlg001 2

# Section range (inclusive)
python -m pi_grapheion.cli extract tlg0059.tlg001 2a-3e

# Page range
python -m pi_grapheion.cli extract tlg0059.tlg001 2-5

# Combine with output styles
python -m pi_grapheion.cli extract tlg0059.tlg001 2a-3e --style S --print
```

**Range Syntax:**
- `2a` - Single section
- `2` - All sections from page 2 (2a, 2b, 2c, 2d, 2e)
- `2a-3e` - Section range from 2a through 3e (inclusive on both ends)
- `2-5` - Page range (all sections from pages 2, 3, 4, and 5)
- Ranges spanning multiple books work seamlessly (e.g., Republic `354a-357b`)

**Note:** Range filtering works with all output styles (A-E, S).

#### Options
```bash
--style, -s    Output style: A, B, C, D, E, S (default: A)
--output, -o   Output file path (default: ./output/<filename>_<style>.txt)
--print        Print to stdout instead of file
--verbose      Show detailed processing information
--debug        Enable debug logging
```

### Output Styles

#### **Style A: Full Modern Edition** (default)
```bash
python -m pi_grapheion.cli extract tlg0059.tlg001 --style A
```
Features:
- All punctuation preserved
- Speaker labels (ΕΥΘ., ΣΩ.) shown when speaker changes
- Stephanus pagination: [2], [b], [c], [d]
- Multi-book works: Title and book headers (ΠΟΛΙΤΕΙΑ Α)
- Text wrapped at 79 characters
- Paragraphs separated by empty lines

Example output:
```
ΕΥΘΥΦΡΩΝ

[2] ΕΥΘ. τί νεώτερον, ὦ Σώκρατες, γέγονεν, ὅτι σὺ τὰς ἐν Λυκείῳ καταλιπὼν
διατριβὰς ἐνθάδε νῦν διατρίβεις περὶ τὴν τοῦ βασιλέως στοάν;

ΣΩ. οὔτοι δὴ Ἀθηναῖοί γε, ὦ Εὐθύφρων, δίκην αὐτὴν καλοῦσιν ἀλλὰ γραφήν.

[b] ΕΥΘ. τί φῄς; γραφὴν σέ τις, ὡς ἔοικε, γέγραπται;
```

#### **Style B: Minimal Punctuation**
```bash
python -m pi_grapheion.cli extract tlg0059.tlg001 --style B
```
Preserves only periods, question marks (;), and colons (·). Removes commas.

#### **Style C: No Punctuation**
```bash
python -m pi_grapheion.cli extract tlg0059.tlg001 --style C
```
Removes all punctuation but preserves speaker labels, word boundaries, and Stephanus markers.

#### **Style D: No Punctuation, No Labels**
```bash
python -m pi_grapheion.cli extract tlg0059.tlg001 --style D
```
Continuous text with Stephanus markers but no speaker labels or punctuation.

#### **Style E: Scriptio Continua**
```bash
python -m pi_grapheion.cli extract tlg0059.tlg001 --style E
```
Ancient Greek as originally written:
- ALL UPPERCASE
- No accents (diacritics removed)
- No word boundaries (no spaces)
- No punctuation
- No speaker labels or apparatus

Example output:
```
ΤΙΝΕΩΤΕΡΟΝΩΣΩΚΡΑΤΕΣΓΕΓΟΝΕΝΟΤΙΣΥΤΑΣΕΝΛΥΚΕΙΩΙΚΑΤΑΛΙΠΩΝΔΙΑΤΡΙΒΑΣΕΝΘΑΔΕΝΥΝ...
```

#### **Style S: Stephanus Layout** (Plato only)
```bash
python -m pi_grapheion.cli extract tlg0059.tlg001 --style S
```
Approximates the 1578 Stephanus edition:
- 40-character narrow columns (Renaissance two-column format)
- Stephanus markers in left margin
- Continuous text flow (no speaker labels)
- **⚠️ Only valid for Plato's works (tlg0059)** - raises error otherwise

Example output:
```
   [2] τί νεώτερον, ὦ Σώκρατες, γέγονεν,
       ὅτι σὺ τὰς ἐν Λυκείῳ καταλιπὼν
       διατριβὰς ἐνθάδε νῦν διατρίβεις
       περὶ τὴν τοῦ βασιλέως στοάν;
   [b] οὔτοι δὴ Ἀθηναῖοί γε, ὦ
       Εὐθύφρων, δίκην αὐτὴν καλοῦσιν
       ἀλλὰ γραφήν.
```

## Examples

### Browse and Extract Workflow
```bash
# 1. Find Plato's works
python -m pi_grapheion.cli search "Plato"

# 2. List all of Plato's works
python -m pi_grapheion.cli list-works tlg0059

# 3. Extract the Euthyphro in different styles
python -m pi_grapheion.cli extract tlg0059.tlg001 --style A --output euthyphro_modern.txt
python -m pi_grapheion.cli extract tlg0059.tlg001 --style E --output euthyphro_ancient.txt

# 4. Preview on console
python -m pi_grapheion.cli extract tlg0059.tlg001 --print | less
```

### Multi-Book Works
```bash
# Plato's Republic (10 books) - automatic book headers
python -m pi_grapheion.cli extract tlg0059.tlg030 --style A

# Output includes:
# ΠΟΛΙΤΕΙΑ
# ΠΟΛΙΤΕΙΑ Α
# [327] ΣΩ. κατέβην χθὲς...
# ...
# ΠΟΛΙΤΕΙΑ Β
# [357] ...
```

### Batch Processing
```bash
# Extract all of Plato's dialogues in Style A
for work in tlg001 tlg002 tlg003 tlg004 tlg005; do
  python -m pi_grapheion.cli extract tlg0059.$work --style A
done
```

## Development

### Project Structure

```
pi-grapheion/
├── pi_grapheion/
│   ├── __init__.py
│   ├── parser.py        # TEI XML parsing with structure validation
│   ├── extractor.py     # Text extraction from parsed XML
│   ├── formatter.py     # Output formatting (styles A-E, S)
│   ├── catalog.py       # Perseus catalog browsing and search
│   ├── exceptions.py    # Custom exceptions
│   └── cli.py           # Command-line interface
├── tests/
│   ├── test_parser.py
│   ├── test_extractor.py
│   ├── test_formatter.py
│   ├── test_catalog.py
│   ├── test_cli.py
│   ├── test_style_validation.py
│   ├── test_stephanus_formatting.py
│   └── fixtures/        # Test XML samples
├── canonical-greekLit/  # Perseus corpus (separate git clone)
│   └── data/
│       ├── tlg0059/     # Plato (36 works)
│       ├── tlg0003/     # Thucydides
│       └── ...          # 99 authors total
├── output/              # Generated text files (gitignored)
├── utils/               # Utility scripts
├── .claude/             # AI assistant guidance
├── pyproject.toml
├── .gitignore
└── README.md
```

### Architecture

Pipeline architecture with clear separation of concerns:

```
XML File → TEIParser → TextExtractor → TextFormatter → Output
              ↓            ↓              ↓
         Validation   Stephanus      Style A-E, S
         Metadata     Speakers       Wrapping
         Structure    Paragraphs     Headers
```

**Core Modules:**
- `parser.py` - TEI XML parsing, structure validation, metadata extraction
- `extractor.py` - Text extraction, Stephanus marker handling, dialogue segmentation
- `formatter.py` - Six output styles with style-specific validation
- `catalog.py` - Browse 99 authors and 818 works, work ID resolution
- `exceptions.py` - `WorkNotFoundError`, `InvalidTEIStructureError`, `EmptyExtractionError`, `InvalidStyleError`
- `cli.py` - Argparse-based CLI with subcommands

### Running Tests

```bash
# Run all 73 tests
pytest

# Run with coverage (current: 64%)
pytest --cov=src --cov-report=term-missing

# Run specific test suite
pytest tests/test_catalog.py -v
pytest tests/test_style_validation.py -v

# Run tests matching pattern
pytest -k "stephanus" -v
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking (if using mypy)
mypy src
```

## Error Handling

The tool provides clear, actionable error messages:

```bash
# Invalid work ID format
$ python -m pi_grapheion.cli extract tlg0059
Error: Work not found: tlg0059
Work ID must be in format 'tlg####.tlg###' (e.g., tlg0059.tlg001)

# Non-existent work
$ python -m pi_grapheion.cli extract tlg0059.tlg999
Error: Work not found: tlg0059.tlg999
Work 'tlg999' not found for author Plato (tlg0059). Available works: 36 total.
Use 'list-works tlg0059' to see all works by this author.

# Invalid style for author
$ python -m pi_grapheion.cli extract tlg0003.tlg001 --style S
Error: Cannot use style 'S (Stephanus layout)': This style is only valid for
Plato's works (tlg0059). Stephanus pagination refers to the 1578 edition of
Plato by Henri Estienne (Stephanus).

# Missing TEI structure
$ python -m pi_grapheion.cli extract broken.xml
Error: Invalid TEI structure in broken.xml: missing required element 'tei:body'

# Empty file
$ python -m pi_grapheion.cli extract empty.xml
Error: No text extracted from empty.xml: No text elements found in document
```

## Special Features

### Stephanus Pagination Format

Stephanus markers use a simplified, reader-friendly format:
- First section of a page: `[2]` (for section 2a)
- Subsequent sections: `[b]`, `[c]`, `[d]` (letter only)

This reduces visual clutter while preserving the ability to cite exact locations.

### Multi-Book Works

For works divided into books (e.g., Republic, Laws):
- Title appears at top in uppercase without accents: `ΠΟΛΙΤΕΙΑ`
- Book headers show title + Greek numeral: `ΠΟΛΙΤΕΙΑ Α`, `ΠΟΛΙΤΕΙΑ Β`
- Automatic detection via TEI `<div type="textpart" subtype="book">`

### Work ID Format

Perseus TLG format: `tlg####.tlg###`
- First part: Author TLG ID (e.g., `tlg0059` = Plato)
- Second part: Work ID (e.g., `tlg001` = Euthyphro)
- Both parts must start with "tlg"

## Catalog Statistics

- **99 authors** from ancient Greece
- **818 works** in Greek
- Authors include: Plato, Aristotle, Thucydides, Herodotus, Homer, Euclid, and more
- Coverage: 8th century BCE to 6th century CE

## Troubleshooting

### Perseus corpus not found
```bash
# Make sure canonical-greekLit is cloned in the project directory
cd pi-grapheion
git clone https://github.com/PerseusDL/canonical-greekLit.git
```

### Virtual environment issues
```bash
# Deactivate and recreate
deactivate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Test failures
```bash
# Ensure Perseus corpus is present
ls canonical-greekLit/data/tlg0059/tlg001/

# If missing, clone it
git clone https://github.com/PerseusDL/canonical-greekLit.git

# Reinstall dependencies
pip install -e ".[dev]"
```
