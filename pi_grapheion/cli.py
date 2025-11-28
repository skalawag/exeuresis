"""Command-line interface for Perseus text extractor."""

import argparse
import logging
import sys
from pathlib import Path

from pi_grapheion.parser import TEIParser
from pi_grapheion.extractor import TextExtractor
from pi_grapheion.formatter import TextFormatter, OutputStyle
from pi_grapheion.catalog import PerseusCatalog
from pi_grapheion.range_filter import RangeFilter
from pi_grapheion.work_resolver import WorkResolver
from pi_grapheion.anthology_extractor import (
    AnthologyExtractor,
    PassageSpec,
    parse_range_list,
)
from pi_grapheion.anthology_formatter import AnthologyFormatter
from pi_grapheion.exceptions import (
    WorkNotFoundError,
    InvalidTEIStructureError,
    EmptyExtractionError,
    InvalidStyleError,
    InvalidStephanusRangeError,
)

logger = logging.getLogger(__name__)


def handle_list_authors(args):
    """Handle the list-authors command."""
    catalog = PerseusCatalog()
    authors = catalog.list_authors()

    if not authors:
        print("No authors found in catalog.", file=sys.stderr)
        return

    print(f"Found {len(authors)} authors:\n")
    for author in authors:
        print(author)


def handle_list_works(args):
    """Handle the list-works command."""
    catalog = PerseusCatalog()

    # Handle --all flag
    if args.all:
        # List all works from all authors
        authors = catalog.list_authors()

        if not authors:
            print("No authors found in catalog.", file=sys.stderr)
            return

        total_works = 0
        for author in authors:
            works = catalog.list_works(author.tlg_id)
            if works:
                print(f"\n{author}")
                print(f"Found {len(works)} works:\n")
                for work in works:
                    print(work)
                total_works += len(works)

        print(f"\n{'='*70}")
        print(f"Total: {len(authors)} authors, {total_works} works")
        return

    # Single author mode
    if not args.author_id:
        print("Error: author_id is required when --all is not specified", file=sys.stderr)
        sys.exit(1)

    # Resolve author name to TLG ID
    author_id = catalog.resolve_author_name(args.author_id)
    if not author_id:
        print(f"Author not found: {args.author_id}", file=sys.stderr)
        print("Use 'list-authors' to see available authors.", file=sys.stderr)
        sys.exit(1)

    # Get author info
    author = catalog.get_author_info(author_id)
    if not author:
        print(f"Author not found: {author_id}", file=sys.stderr)
        sys.exit(1)

    print(f"{author}\n")

    # Get works
    works = catalog.list_works(author_id)
    if not works:
        print(f"No works found for {author_id}", file=sys.stderr)
        return

    print(f"Found {len(works)} works:\n")
    for work in works:
        print(work)


def handle_search(args):
    """Handle the search command."""
    catalog = PerseusCatalog()
    results = catalog.search_works(args.query)

    if not results:
        print(f"No results found for '{args.query}'", file=sys.stderr)
        return

    print(f"Found {len(results)} matches for '{args.query}':\n")

    current_author = None
    for author, work in results:
        # Print author header if we're on a new author
        if current_author is None or current_author.tlg_id != author.tlg_id:
            print(f"\n{author}")
            current_author = author
        print(work)


def parse_anthology_args(input_files, passage_specs):
    """
    Parse anthology arguments into PassageSpec objects.

    Args:
        input_files: List of work names/IDs from positional arguments
        passage_specs: List of range specifications from --passages flags

    Returns:
        List of PassageSpec objects

    The syntax is: work1 --passages ranges1 work2 --passages ranges2
    """
    if not passage_specs:
        return None

    # Match work names with passage specs
    # Each work is followed by a --passages flag
    passages = []
    work_idx = 0

    for passage_spec in passage_specs:
        if work_idx >= len(input_files):
            raise ValueError(
                "Error: --passages flag without corresponding work name. "
                "Syntax: work1 --passages ranges1 work2 --passages ranges2"
            )

        work_name = str(input_files[work_idx])
        ranges = parse_range_list(passage_spec)
        passages.append(PassageSpec(work_id=work_name, ranges=ranges))
        work_idx += 1

    return passages


def handle_anthology_extract(args):
    """Handle anthology extraction mode."""
    # Collect all work names from input_file
    # In anthology mode, the optional 'range' positional may capture additional work names
    work_names = list(args.input_file)
    if args.range:
        # In anthology mode, 'range' is actually another work name
        work_names.append(args.range)

    # Parse anthology arguments
    try:
        passage_specs = parse_anthology_args(work_names, args.passage_specs)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    # Resolve work names to TLG IDs
    resolver = WorkResolver()
    resolved_passages = []
    for spec in passage_specs:
        try:
            work_id = resolver.resolve(spec.work_id)
            resolved_passages.append(PassageSpec(work_id=work_id, ranges=spec.ranges))
        except WorkNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Map style argument
    style_map = {
        "A": OutputStyle.FULL_MODERN,
        "full_modern": OutputStyle.FULL_MODERN,
        "B": OutputStyle.MINIMAL_PUNCTUATION,
        "minimal_punctuation": OutputStyle.MINIMAL_PUNCTUATION,
        "C": OutputStyle.NO_PUNCTUATION,
        "no_punctuation": OutputStyle.NO_PUNCTUATION,
        "D": OutputStyle.NO_PUNCTUATION_NO_LABELS,
        "no_punctuation_no_labels": OutputStyle.NO_PUNCTUATION_NO_LABELS,
        "E": OutputStyle.SCRIPTIO_CONTINUA,
        "scriptio_continua": OutputStyle.SCRIPTIO_CONTINUA,
        "S": OutputStyle.STEPHANUS_LAYOUT,
        "stephanus_layout": OutputStyle.STEPHANUS_LAYOUT,
    }
    output_style = style_map[args.style]

    # Determine output destination
    output_to_stdout = args.print or (args.output and str(args.output) == "-")

    if args.verbose:
        print(f"Anthology extraction mode", file=sys.stderr)
        print(f"Extracting {len(resolved_passages)} work(s)", file=sys.stderr)
        print(f"Style: {output_style.value}", file=sys.stderr)

    try:
        # Extract anthology blocks
        extractor = AnthologyExtractor()
        blocks = extractor.extract_passages(resolved_passages)

        # Format blocks
        formatter = AnthologyFormatter(style=output_style)
        output_text = formatter.format_blocks(blocks)

        # Output
        if output_to_stdout:
            print(output_text)
        else:
            # Generate default output filename
            if args.output:
                output_file = args.output
            else:
                output_dir = Path("output")
                output_dir.mkdir(exist_ok=True)
                style_suffix = args.style.upper() if len(args.style) == 1 else args.style
                output_file = output_dir / f"anthology_{style_suffix}.txt"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output_text)

            print(f"Anthology written to: {output_file}", file=sys.stderr)

    except InvalidStyleError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if args.debug if hasattr(args, 'debug') else False:
            raise
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_extract(args):
    """Handle the extract command (supports both single extraction and anthology)."""
    # Check if we're in anthology mode
    if hasattr(args, 'passage_specs') and args.passage_specs:
        handle_anthology_extract(args)
        return

    # Original single-extraction mode
    # input_file is a list due to nargs='+', take first element
    input_files_list = args.input_file if isinstance(args.input_file, list) else [args.input_file]
    input_file_arg = Path(input_files_list[0])

    # If there are 2 elements in input_file, the second is the range
    # (This happens when: extract file.xml 2a)
    if len(input_files_list) == 2 and args.range is None:
        args.range = input_files_list[1]

    input_str = str(input_file_arg)

    # Track work_id for error messages
    work_id = ""

    # Check if this is a file path (contains / or ends with .xml)
    if "/" in input_str or input_str.endswith(".xml"):
        # It's a file path, use it directly
        input_file = input_file_arg
    else:
        # It could be a work ID or work name alias
        # Try to resolve it using WorkResolver
        try:
            resolver = WorkResolver()
            work_id = resolver.resolve(input_str)

            # Now resolve the work ID to a file path
            catalog = PerseusCatalog()
            input_file = catalog.resolve_work_id(work_id)

            if args.verbose:
                if input_str != work_id:
                    print(f"Resolved work name '{input_str}' to work ID '{work_id}'", file=sys.stderr)
                print(f"Resolved work ID '{work_id}' to: {input_file}", file=sys.stderr)
        except WorkNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate input file exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # Map style argument to OutputStyle enum
    style_map = {
        "A": OutputStyle.FULL_MODERN,
        "full_modern": OutputStyle.FULL_MODERN,
        "B": OutputStyle.MINIMAL_PUNCTUATION,
        "minimal_punctuation": OutputStyle.MINIMAL_PUNCTUATION,
        "C": OutputStyle.NO_PUNCTUATION,
        "no_punctuation": OutputStyle.NO_PUNCTUATION,
        "D": OutputStyle.NO_PUNCTUATION_NO_LABELS,
        "no_punctuation_no_labels": OutputStyle.NO_PUNCTUATION_NO_LABELS,
        "E": OutputStyle.SCRIPTIO_CONTINUA,
        "scriptio_continua": OutputStyle.SCRIPTIO_CONTINUA,
        "S": OutputStyle.STEPHANUS_LAYOUT,
        "stephanus_layout": OutputStyle.STEPHANUS_LAYOUT,
    }

    output_style = style_map[args.style]

    # Determine output destination
    output_to_stdout = args.print or (args.output and str(args.output) == "-")

    if output_to_stdout:
        output_file = None
    elif args.output:
        output_file = args.output
    else:
        # Generate default output filename in ./output/ directory
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        style_suffix = args.style.upper() if len(args.style) == 1 else args.style
        output_file = output_dir / f"{input_file.stem}_{style_suffix}.txt"

    # Warn if trying to write to canonical-greekLit directory
    if output_file and "canonical-greekLit" in str(output_file):
        print(
            "Warning: You are writing to the canonical-greekLit source directory.",
            file=sys.stderr,
        )
        print(
            "This is not recommended. Consider using --output to specify a different location.",
            file=sys.stderr,
        )
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            print("Aborted.", file=sys.stderr)
            sys.exit(0)

    if args.verbose:
        print(f"Processing: {input_file}", file=sys.stderr)
        print(f"Style: {output_style.value}", file=sys.stderr)
        if output_to_stdout:
            print(f"Output: stdout", file=sys.stderr)
        else:
            print(f"Output: {output_file}", file=sys.stderr)

    try:
        # Parse XML
        if args.verbose:
            print("Parsing XML...", file=sys.stderr)
        parser_obj = TEIParser(input_file)

        # Extract text
        if args.verbose:
            print("Extracting dialogue...", file=sys.stderr)
        extractor = TextExtractor(parser_obj)

        # For Stephanus layout style, we need inline milestones
        # For other styles, use regular dialogue extraction
        # Actually, ALL styles need inline milestones to show markers correctly
        if output_style == OutputStyle.STEPHANUS_LAYOUT:
            # Style S needs special handling with extractor reference
            dialogue = extractor.get_dialogue_text()
        else:
            # Other styles should use inline milestones for correct marker placement
            dialogue = extractor.get_dialogue_text()

        # Apply range filter if specified
        if args.range:
            if args.verbose:
                print(f"Filtering to range: {args.range}", file=sys.stderr)
            range_filter = RangeFilter()
            dialogue = range_filter.filter(dialogue, args.range, work_id=work_id)
            if args.verbose:
                print(f"Filtered to {len(dialogue)} dialogue entries", file=sys.stderr)

        if args.verbose:
            print(f"Found {len(dialogue)} dialogue entries", file=sys.stderr)

        # Format output
        if args.verbose:
            print("Formatting text...", file=sys.stderr)
        formatter = TextFormatter(dialogue, extractor=extractor, parser=parser_obj)
        formatted_text = formatter.format(output_style)

        # Output the text
        if output_to_stdout:
            # Print to console
            print(formatted_text)
        else:
            # Write to file
            if args.verbose:
                print(f"Writing to {output_file}...", file=sys.stderr)
            output_file.write_text(formatted_text, encoding="utf-8")

            print(f"Successfully created: {output_file}")

            if args.verbose:
                print(f"Output size: {len(formatted_text)} characters", file=sys.stderr)

    except (InvalidTEIStructureError, EmptyExtractionError, InvalidStyleError, InvalidStephanusRangeError) as e:
        # Custom exceptions with clear user messages
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        # Unexpected errors
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="perseus",
        description="Extract and reformat Greek texts from Perseus Digital Library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Browse the catalog
  %(prog)s list-authors                    # List all 99 authors
  %(prog)s list-works tlg0059              # List Plato's works
  %(prog)s list-works --all                # List all works (818 total)
  %(prog)s search "Republic"               # Search by title
  %(prog)s search "Plato"                  # Search by author

  # Extract texts
  %(prog)s extract tlg0059.tlg001          # Extract Euthyphro by work ID
  %(prog)s extract input.xml               # Extract from file path
  %(prog)s extract tlg0059.tlg030 -s A     # Extract Republic, style A
  %(prog)s extract tlg0059.tlg004 --print  # Print Phaedo to stdout
  %(prog)s extract tlg0059.tlg001 2a-3e    # Extract specific range

  # Different output styles
  %(prog)s extract tlg0059.tlg001 -s A     # Full modern edition (default)
  %(prog)s extract tlg0059.tlg001 -s D     # No punctuation, no labels
  %(prog)s extract tlg0059.tlg001 -s E     # Scriptio continua (ancient style)
  %(prog)s extract tlg0059.tlg001 -s S     # Stephanus layout (1578 edition)

For detailed help on any command, use:
  %(prog)s <command> --help
        """,
    )

    # Add global debug flag
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging output"
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Extract subcommand (default behavior)
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract and format text from TEI XML file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Style Options:
  A, full_modern                Full modern edition with all punctuation, speaker labels,
                                and Stephanus pagination markers (default)
  B, minimal_punctuation        Minimal punctuation (periods and question marks only)
  C, no_punctuation             No punctuation but preserves speaker labels and spacing
  D, no_punctuation_no_labels   No punctuation, no speaker labels, continuous text
  E, scriptio_continua          Ancient Greek continuous text: uppercase, no spaces,
                                no punctuation, no apparatus
  S, stephanus_layout           Approximates 1578 Stephanus edition: 40-char columns
                                with section markers in left margin

Examples:
  %(prog)s extract input.xml
  %(prog)s extract input.xml --style D
  %(prog)s extract input.xml 327a-328c          # Extract specific range
  %(prog)s extract tlg0059.tlg001 327a --print  # Extract single section
  %(prog)s extract tlg0059.tlg001 --style A     # Extract by work ID
        """,
    )
    extract_parser.add_argument(
        "input_file",
        nargs='+',
        help="Path to TEI XML file, work ID (e.g., tlg0059.tlg001), or work name(s) for anthology",
    )
    extract_parser.add_argument(
        "range",
        nargs="?",
        default=None,
        help="Optional Stephanus range (e.g., '327a', '327-329', '327a-328c')",
    )
    extract_parser.add_argument(
        "--passages",
        action="append",
        dest="passage_specs",
        metavar="RANGES",
        help="Anthology mode: comma-separated ranges for preceding work (e.g., --passages 5a,7b-c)",
    )
    extract_parser.add_argument(
        "-s",
        "--style",
        type=str,
        default="A",
        choices=[
            "A",
            "B",
            "C",
            "D",
            "E",
            "S",
            "full_modern",
            "minimal_punctuation",
            "no_punctuation",
            "no_punctuation_no_labels",
            "scriptio_continua",
            "stephanus_layout",
        ],
        help="Output style (default: A)",
    )
    extract_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file path (default: output/<input>_<style>.txt). Use '-' for stdout.",
    )
    extract_parser.add_argument(
        "-p",
        "--print",
        action="store_true",
        help="Print to console (stdout) instead of file",
    )
    extract_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    extract_parser.set_defaults(func=handle_extract)

    # List authors subcommand
    list_authors_parser = subparsers.add_parser(
        "list-authors", help="List all authors in the catalog"
    )
    list_authors_parser.set_defaults(func=handle_list_authors)

    # List works subcommand
    list_works_parser = subparsers.add_parser(
        "list-works", help="List all works for a specific author or all works with --all"
    )
    list_works_parser.add_argument(
        "author_id",
        nargs="?",
        help="Author TLG ID (e.g., tlg0059 for Plato). Optional if --all is used."
    )
    list_works_parser.add_argument(
        "--all",
        action="store_true",
        help="List all works from all authors"
    )
    list_works_parser.set_defaults(func=handle_list_works)

    # Search subcommand
    search_parser = subparsers.add_parser(
        "search", help="Search for works by title or author name"
    )
    search_parser.add_argument("query", help="Search query (case-insensitive)")
    search_parser.set_defaults(func=handle_search)

    # Check for backward compatibility (old-style invocation without subcommand)
    # If first arg looks like a file path (contains / or ends with .xml), insert 'extract'
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        valid_commands = {"extract", "list-authors", "list-works", "search"}
        if first_arg not in valid_commands and (
            "/" in first_arg or first_arg.endswith(".xml")
        ):
            # Old-style invocation: python -m pi_grapheion.cli input.xml
            # Insert 'extract' as the subcommand
            sys.argv.insert(1, "extract")

    # Parse arguments
    args = parser.parse_args()

    # Configure logging based on --debug flag
    if args.debug:
        # DEBUG level shows all messages including debug info
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(levelname)s] %(name)s: %(message)s"
        )
        logger.debug("Debug mode enabled")
    else:
        # WARNING level shows only warnings and errors (not info)
        logging.basicConfig(
            level=logging.WARNING,
            format="[%(levelname)s] %(message)s"
        )

    # If no command specified, show help
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Call the appropriate handler
    args.func(args)


if __name__ == "__main__":
    main()
