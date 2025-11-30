"""Command-line interface for Perseus text extractor."""

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

from exeuresis.anthology_extractor import (
    AnthologyExtractor,
    PassageSpec,
    parse_range_list,
)
from exeuresis.anthology_formatter import AnthologyFormatter
from exeuresis.catalog import PerseusCatalog
from exeuresis.cli_catalog import (
    filter_authors,
    filter_works,
    format_authors_table,
    format_works_table,
    paginate,
    parse_filter,
)
from exeuresis.config import CorpusConfig, get_corpora, get_default_corpus_name
from exeuresis.corpus_health import (
    CorpusHealthResult,
    CorpusHealthStatus,
    check_corpus,
)
from exeuresis.exceptions import (
    EmptyExtractionError,
    InvalidStephanusRangeError,
    InvalidStyleError,
    InvalidTEIStructureError,
    WorkNotFoundError,
)
from exeuresis.extractor import TextExtractor
from exeuresis.formatter import OutputStyle
from exeuresis.output_writers import JSONLWriter, JSONWriter, TextWriter
from exeuresis.parser import TEIParser
from exeuresis.range_filter import RangeFilter
from exeuresis.work_resolver import WorkResolver

logger = logging.getLogger(__name__)

STATUS_ICONS = {
    CorpusHealthStatus.OK: "✓",
    CorpusHealthStatus.WARNING: "⚠",
    CorpusHealthStatus.ERROR: "✗",
}


def parse_wrap_arg(value):
    """Parse --wrap argument, allowing integers or 'off'/0 for no wrapping."""

    if isinstance(value, int):
        if value < 0:
            raise argparse.ArgumentTypeError(
                "wrap width must be positive or 0 to disable"
            )
        return value or None

    if value is None:
        return 79

    str_value = str(value).strip().lower()

    if str_value in {"off", "none", "disable"}:
        return None

    try:
        width = int(str_value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise argparse.ArgumentTypeError(
            "wrap width must be an integer or 'off'"
        ) from exc

    if width < 0:
        raise argparse.ArgumentTypeError("wrap width must be positive or 0 to disable")

    return width or None


def _print_works_table(works):
    """Print works in tabular format."""
    if not works:
        return

    # Get terminal width
    terminal_width = shutil.get_terminal_size(fallback=(80, 24)).columns

    # Calculate natural column widths
    natural_title_width = max(
        len(f"{w.title_en} ({w.title_grc})" if w.title_grc else w.title_en)
        for w in works
    )
    natural_title_width = max(natural_title_width, len("Title"))

    sections_width = max(len(w.page_range) if w.page_range else 0 for w in works)
    sections_width = max(sections_width, len("Sections"))

    # Work ID format: tlg0059.tlg001
    work_id_width = max(len(f"{w.tlg_id}.{w.work_id}") for w in works)
    work_id_width = max(work_id_width, len("File"))

    # Calculate available width for title (leave 4 chars for separators)
    fixed_width = sections_width + work_id_width + 4
    available_title_width = terminal_width - fixed_width

    # Set title width (minimum 30, max terminal allows)
    title_width = max(30, min(natural_title_width, available_title_width))

    # Helper function to truncate title if needed
    def format_title(work):
        title = (
            f"{work.title_en} ({work.title_grc})" if work.title_grc else work.title_en
        )
        if len(title) > title_width:
            return title[: title_width - 3] + "..."
        return title

    # Print header
    header = f"{'Title':<{title_width}}  {'Sections':<{sections_width}}  {'File':<{work_id_width}}"
    print(header)
    print("-" * len(header))

    # Print rows
    for work in works:
        title = format_title(work)
        sections = work.page_range if work.page_range else ""
        file_id = f"{work.tlg_id}.{work.work_id}"
        print(
            f"{title:<{title_width}}  {sections:<{sections_width}}  {file_id:<{work_id_width}}"
        )


def _print_corpus_health(
    display_name: str,
    corpus_config,
    result: CorpusHealthResult,
    *,
    detailed: bool,
):
    """Render corpus health information."""

    icon = STATUS_ICONS.get(result.status, "•")

    if not detailed:
        print(f"* {display_name} {icon} [{result.status.value}] {result.message}")
        return

    print(f"* {display_name}")
    print(f"    Path: {result.path}")
    if getattr(corpus_config, "description", None):
        print(f"    Description: {corpus_config.description}")
    print(f"    Status: {result.status.value} — {result.message}")
    print(f"    Authors: {result.total_authors}")
    print(f"    Works: {result.total_works}")
    print(f"    Files: {result.total_files}")

    sample_info = f"{result.checked_files}"
    if result.mode == "quick":
        extras = []
        if result.sample_percent is not None:
            extras.append(f"{result.sample_percent:g}%")
        if result.seed is not None:
            extras.append(f"seed={result.seed}")
        suffix = "quick sample"
        if extras:
            suffix += f" ({', '.join(extras)})"
        print(f"    Checked: {sample_info} — {suffix}")
    else:
        print(f"    Checked: {sample_info} — full walk")

    if result.metadata_issues:
        print("    Metadata issues:")
        for issue in result.metadata_issues[:5]:
            print(f"      - {issue}")
        if len(result.metadata_issues) > 5:
            print(f"      … {len(result.metadata_issues) - 5} more")

    if result.failed_files:
        print("    Parse failures:")
        for failure in result.failed_files[:5]:
            print(f"      - {failure.work_id}: {failure.error}")
        if len(result.failed_files) > 5:
            print(f"      … {len(result.failed_files) - 5} more")


def handle_list_authors(args):
    """Handle the list-authors command."""
    catalog = PerseusCatalog(corpus_name=args.corpus)
    all_authors = catalog.list_authors()

    if not all_authors:
        print("No authors found in catalog.", file=sys.stderr)
        return

    # Parse columns
    columns = None
    if hasattr(args, "columns") and args.columns:
        columns = [c.strip() for c in args.columns.split(",")]

    # Parse and apply filters
    filtered_authors = all_authors
    if hasattr(args, "filters") and args.filters:
        try:
            parsed_filters = [parse_filter(f) for f in args.filters]
            filtered_authors = filter_authors(all_authors, parsed_filters)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Apply pagination
    limit = getattr(args, "limit", None)
    offset = getattr(args, "offset", 0)
    paginated = paginate(filtered_authors, limit=limit, offset=offset)

    # Show results
    if not paginated:
        if offset > 0:
            print(
                f"No results (offset {offset} beyond {len(filtered_authors)} authors)",
                file=sys.stderr,
            )
        else:
            print("No authors match the filters.", file=sys.stderr)
        return

    # Show count/pagination info
    if hasattr(args, "filters") and args.filters:
        if limit:
            print(
                f"Showing {offset + 1}-{offset + len(paginated)} of {len(filtered_authors)} authors "
                f"(filtered from {len(all_authors)})\n"
            )
        else:
            print(
                f"Found {len(filtered_authors)} of {len(all_authors)} authors (filtered)\n"
            )
    else:
        if limit:
            print(
                f"Showing {offset + 1}-{offset + len(paginated)} of {len(all_authors)} authors\n"
            )
        else:
            print(f"Found {len(all_authors)} authors:\n")

    # Format and print
    try:
        output = format_authors_table(paginated, columns=columns)
        print(output)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_list_works(args):
    """Handle the list-works command."""
    catalog = PerseusCatalog(corpus_name=args.corpus)

    # Parse columns
    columns = None
    if hasattr(args, "columns") and args.columns:
        columns = [c.strip() for c in args.columns.split(",")]

    # Handle --all flag
    if args.all:
        # List all works from all authors
        authors = catalog.list_authors()

        if not authors:
            print("No authors found in catalog.", file=sys.stderr)
            return

        # Collect all works from all authors
        all_works = []
        for author in authors:
            works = catalog.list_works(author.tlg_id)
            all_works.extend(works)

        # Parse and apply filters
        filtered_works = all_works
        if hasattr(args, "filters") and args.filters:
            try:
                parsed_filters = [parse_filter(f) for f in args.filters]
                filtered_works = filter_works(all_works, parsed_filters)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        # Apply pagination
        limit = getattr(args, "limit", None)
        offset = getattr(args, "offset", 0)
        paginated = paginate(filtered_works, limit=limit, offset=offset)

        # Show results
        if not paginated:
            if offset > 0:
                print(
                    f"No results (offset {offset} beyond {len(filtered_works)} works)",
                    file=sys.stderr,
                )
            else:
                print("No works match the filters.", file=sys.stderr)
            return

        # Show count/pagination info
        if hasattr(args, "filters") and args.filters:
            if limit:
                print(
                    f"Showing {offset + 1}-{offset + len(paginated)} of {len(filtered_works)} works "
                    f"(filtered from {len(all_works)})\n"
                )
            else:
                print(
                    f"Found {len(filtered_works)} of {len(all_works)} works (filtered)\n"
                )
        else:
            if limit:
                print(
                    f"Showing {offset + 1}-{offset + len(paginated)} of {len(all_works)} works\n"
                )
            else:
                print(f"Found {len(all_works)} works:\n")

        # Format and print
        try:
            output = format_works_table(paginated, columns=columns)
            if output is None:
                # Use legacy formatting
                _print_works_table(paginated)
            else:
                print(output)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        return

    # Single author mode
    if not args.author_id:
        print(
            "Error: author_id is required when --all is not specified", file=sys.stderr
        )
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

    # Get all works for this author
    all_works = catalog.list_works(author_id)
    if not all_works:
        print(f"No works found for {author_id}", file=sys.stderr)
        return

    # Parse and apply filters
    filtered_works = all_works
    if hasattr(args, "filters") and args.filters:
        try:
            parsed_filters = [parse_filter(f) for f in args.filters]
            filtered_works = filter_works(all_works, parsed_filters)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Apply pagination
    limit = getattr(args, "limit", None)
    offset = getattr(args, "offset", 0)
    paginated = paginate(filtered_works, limit=limit, offset=offset)

    # Show results
    if not paginated:
        if offset > 0:
            print(
                f"No results (offset {offset} beyond {len(filtered_works)} works)",
                file=sys.stderr,
            )
        else:
            print("No works match the filters.", file=sys.stderr)
        return

    # Print author header
    print(f"{author}\n")

    # Show count/pagination info
    if hasattr(args, "filters") and args.filters:
        if limit:
            print(
                f"Showing {offset + 1}-{offset + len(paginated)} of {len(filtered_works)} works "
                f"(filtered from {len(all_works)})\n"
            )
        else:
            print(f"Found {len(filtered_works)} of {len(all_works)} works (filtered)\n")
    else:
        if limit:
            print(
                f"Showing {offset + 1}-{offset + len(paginated)} of {len(all_works)} works\n"
            )
        else:
            print(f"Found {len(all_works)} works:\n")

    # Format and print
    try:
        output = format_works_table(paginated, columns=columns)
        if output is None:
            # Use legacy formatting
            _print_works_table(paginated)
        else:
            print(output)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_search(args):
    """Handle the search command."""
    catalog = PerseusCatalog(corpus_name=args.corpus)
    results = catalog.search_works(args.query)

    if not results:
        print(f"No results found for '{args.query}'", file=sys.stderr)
        return

    print(f"Found {len(results)} matches for '{args.query}':\n")

    # Group works by author
    author_works = {}
    for author, work in results:
        if author.tlg_id not in author_works:
            author_works[author.tlg_id] = (author, [])
        author_works[author.tlg_id][1].append(work)

    # Print each author with their works as a table
    for author, works in author_works.values():
        print(f"\n{author}")
        _print_works_table(works)


def handle_list_corpora(args):
    """Handle the list-corpora command."""
    corpora = get_corpora()
    default_name = get_default_corpus_name()
    extra_paths = [Path(p) for p in getattr(args, "extra_corpora", []) or []]

    if not corpora and not extra_paths:
        print("No corpora configured.", file=sys.stderr)
        return

    print("Configured corpora:\n")

    entries = []
    has_existing_path = False

    for name, corpus_config in sorted(corpora.items()):
        entries.append((name, corpus_config, False))
        if corpus_config.path.exists():
            has_existing_path = True

    for idx, path in enumerate(extra_paths, start=1):
        name = str(path)
        entries.append(
            (
                name,
                CorpusConfig(
                    name=name,
                    path=path,
                    description="Provided via --corpus",
                ),
                True,
            )
        )
        if path.exists():
            has_existing_path = True

    if has_existing_path:
        filtered_entries = []
        for name, corpus_config, is_manual in entries:
            if corpus_config.path.exists() or is_manual:
                filtered_entries.append((name, corpus_config))
        entries_to_display = filtered_entries or [
            (name, config) for name, config, _ in entries
        ]
    else:
        entries_to_display = [(name, config) for name, config, _ in entries]

    for name, corpus_config in entries_to_display:
        display_name = f"{name} (default)" if name == default_name else name
        result = check_corpus(corpus_config, mode="quick")
        _print_corpus_health(
            display_name,
            corpus_config,
            result,
            detailed=getattr(args, "details", False),
        )
        print()


def handle_check_corpus(args):
    """Handle the check-corpus command."""
    corpora = get_corpora()
    default_name = get_default_corpus_name()

    manual_arg = getattr(args, "target_corpus", None) or getattr(args, "corpus", None)
    manual_config = None
    corpus_config = None

    if manual_arg:
        if manual_arg in corpora:
            corpus_config = corpora[manual_arg]
        else:
            path_candidate = Path(manual_arg).expanduser()
            if (
                "/" in manual_arg
                or manual_arg.startswith(".")
                or path_candidate.exists()
            ):
                manual_config = CorpusConfig(
                    name=str(path_candidate),
                    path=path_candidate,
                    description="Provided via --corpus",
                )
                corpus_config = manual_config
            elif not corpora:
                print(f"Corpus '{manual_arg}' not found.", file=sys.stderr)
                print(
                    "No corpora configured. Provide a path via --corpus.",
                    file=sys.stderr,
                )
                sys.exit(1)
            else:
                print(f"Corpus '{manual_arg}' not found.", file=sys.stderr)
                available = ", ".join(sorted(corpora.keys()))
                print(f"Available corpora: {available}", file=sys.stderr)
                sys.exit(1)

    if corpus_config is None:
        if default_name in corpora:
            corpus_config = corpora[default_name]
        elif corpora:
            first_name = sorted(corpora.keys())[0]
            corpus_config = corpora[first_name]
        else:
            print(
                "No corpora configured and no --corpus path provided.", file=sys.stderr
            )
            sys.exit(1)

    if args.mode == "full" and args.sample_percent is not None:
        print("--sample-percent is only valid in quick mode", file=sys.stderr)
        sys.exit(1)

    if args.sample_percent is not None and args.sample_percent <= 0:
        print("--sample-percent must be positive", file=sys.stderr)
        sys.exit(1)

    result = check_corpus(
        corpus_config,
        mode=args.mode,
        sample_percent=args.sample_percent if args.mode == "quick" else None,
        seed=args.seed,
    )

    display_name = corpus_config.name
    if default_name and corpus_config.name == default_name:
        display_name = f"{display_name} (default)"

    _print_corpus_health(display_name, corpus_config, result, detailed=True)
    print()

    if result.status is CorpusHealthStatus.ERROR:
        sys.exit(1)


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
    wrap_width = getattr(args, "wrap_width", 79)
    output_format = getattr(args, "format", "text")

    # Determine output destination
    output_to_stdout = args.print or (args.output and str(args.output) == "-")

    if args.verbose:
        print("Anthology extraction mode", file=sys.stderr)
        print(f"Extracting {len(resolved_passages)} work(s)", file=sys.stderr)
        if output_format == "text":
            print(f"Style: {output_style.value}", file=sys.stderr)
        else:
            print(f"Format: {output_format}", file=sys.stderr)

    try:
        # Extract anthology blocks
        extractor = AnthologyExtractor(corpus_name=args.corpus)
        blocks = extractor.extract_passages(resolved_passages)

        # Format based on output format
        if output_format == "json":
            # JSON format: create metadata and flatten blocks
            metadata = {
                "anthology": True,
                "num_works": len(blocks),
                "extraction_timestamp": datetime.now().isoformat(),
                "format_version": "1.0",
            }

            # Flatten blocks into segments with block metadata
            all_segments = []
            for block_idx, block in enumerate(blocks):
                for segment in block.segments:
                    segment_with_block = segment.copy()
                    segment_with_block["block_index"] = block_idx
                    segment_with_block["work_id"] = block.work_id
                    segment_with_block["work_title_en"] = block.work_title_en
                    segment_with_block["work_title_gr"] = block.work_title_gr
                    segment_with_block["range_display"] = block.range_display
                    if block.book:
                        segment_with_block["work_book"] = block.book
                    all_segments.append(segment_with_block)

            writer = JSONWriter()
            output_text = writer.format(all_segments, metadata=metadata)
        elif output_format == "jsonl":
            # JSONL format: flatten blocks with block metadata
            all_segments = []
            for block_idx, block in enumerate(blocks):
                for segment in block.segments:
                    segment_with_block = segment.copy()
                    segment_with_block["block_index"] = block_idx
                    segment_with_block["work_id"] = block.work_id
                    segment_with_block["work_title_en"] = block.work_title_en
                    segment_with_block["work_title_gr"] = block.work_title_gr
                    segment_with_block["range_display"] = block.range_display
                    if block.book:
                        segment_with_block["work_book"] = block.book
                    all_segments.append(segment_with_block)

            writer = JSONLWriter()
            output_text = writer.format(all_segments)
        else:
            # Text format (default)
            formatter = AnthologyFormatter(style=output_style, wrap_width=wrap_width)
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

                if output_format == "json":
                    output_file = output_dir / "anthology_json.json"
                elif output_format == "jsonl":
                    output_file = output_dir / "anthology_jsonl.jsonl"
                else:
                    style_suffix = (
                        args.style.upper() if len(args.style) == 1 else args.style
                    )
                    output_file = output_dir / f"anthology_{style_suffix}.txt"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output_text)

            print(f"Anthology written to: {output_file}", file=sys.stderr)

    except InvalidStyleError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if args.debug if hasattr(args, "debug") else False:
            raise
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_extract(args):
    """Handle the extract command (supports both single extraction and anthology)."""
    # Check if we're in anthology mode
    if hasattr(args, "passage_specs") and args.passage_specs:
        handle_anthology_extract(args)
        return

    # Original single-extraction mode
    # input_file is a list due to nargs='+', take first element
    input_files_list = (
        args.input_file if isinstance(args.input_file, list) else [args.input_file]
    )
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
            resolver = WorkResolver(corpus_name=args.corpus)
            work_id = resolver.resolve(input_str)

            # Now resolve the work ID to a file path
            catalog = PerseusCatalog(corpus_name=args.corpus)
            input_file = catalog.resolve_work_id(work_id)

            if args.verbose:
                if input_str != work_id:
                    print(
                        f"Resolved work name '{input_str}' to work ID '{work_id}'",
                        file=sys.stderr,
                    )
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
    wrap_width = getattr(args, "wrap_width", 79)
    output_format = getattr(args, "format", "text")

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

        if output_format == "json":
            output_file = output_dir / f"{input_file.stem}_json.json"
        elif output_format == "jsonl":
            output_file = output_dir / f"{input_file.stem}_jsonl.jsonl"
        else:
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
            print("Output: stdout", file=sys.stderr)
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

        # Format output based on selected format
        if args.verbose:
            print(f"Formatting output as {output_format}...", file=sys.stderr)

        if output_format == "json":
            # JSON format with metadata
            metadata = {
                "work_id": work_id or str(input_file.stem),
                "title": parser_obj.get_title() if parser_obj else "",
                "extraction_timestamp": datetime.now().isoformat(),
                "format_version": "1.0",
            }
            if args.range:
                metadata["range"] = args.range

            writer = JSONWriter()
            formatted_output = writer.format(dialogue, metadata=metadata)
        elif output_format == "jsonl":
            # JSONL format (no metadata wrapper)
            writer = JSONLWriter()
            formatted_output = writer.format(dialogue)
        else:
            # Text format (default)
            writer = TextWriter(
                style=output_style,
                wrap_width=wrap_width,
                extractor=extractor,
                parser=parser_obj,
            )
            formatted_output = writer.format(dialogue)

        # Output the formatted text
        if output_to_stdout:
            # Print to console
            print(formatted_output)
        else:
            # Write to file
            if args.verbose:
                print(f"Writing to {output_file}...", file=sys.stderr)
            output_file.write_text(formatted_output, encoding="utf-8")

            print(f"Successfully created: {output_file}")

            if args.verbose:
                print(
                    f"Output size: {len(formatted_output)} characters", file=sys.stderr
                )

    except (
        InvalidTEIStructureError,
        EmptyExtractionError,
        InvalidStyleError,
        InvalidStephanusRangeError,
    ) as e:
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
        prog="exeuresis",
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

    # Add global flags
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging output"
    )
    parser.add_argument(
        "--corpus",
        metavar="NAME",
        help='Corpus to use (default: from config or "default")',
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
        nargs="+",
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
        "-f",
        "--format",
        type=str,
        default="text",
        choices=["text", "json", "jsonl"],
        help="Output format: text (default), json (array with metadata), jsonl (newline-delimited)",
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
    extract_parser.add_argument(
        "--wrap",
        "--wrap-width",
        dest="wrap_width",
        type=parse_wrap_arg,
        default=79,
        help="Wrap output to N columns (default: 79). Use 0 or 'off' to disable wrapping.",
    )
    extract_parser.set_defaults(func=handle_extract)

    # List authors subcommand
    list_authors_parser = subparsers.add_parser(
        "list-authors", help="List all authors in the catalog"
    )
    list_authors_parser.add_argument(
        "--columns",
        type=str,
        help="Comma-separated list of columns (e.g., tlg_id,name_en). Use 'all' for all fields.",
    )
    list_authors_parser.add_argument(
        "--filter",
        action="append",
        dest="filters",
        metavar="FIELD=VALUE",
        help="Filter by field. Use '=' for exact or '~' for contains. Repeatable.",
    )
    list_authors_parser.add_argument(
        "--limit", type=int, help="Maximum number of results to show"
    )
    list_authors_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of results to skip (for pagination)",
    )
    list_authors_parser.set_defaults(func=handle_list_authors)

    # List works subcommand
    list_works_parser = subparsers.add_parser(
        "list-works",
        help="List all works for a specific author or all works with --all",
    )
    list_works_parser.add_argument(
        "author_id",
        nargs="?",
        help="Author TLG ID (e.g., tlg0059 for Plato). Optional if --all is used.",
    )
    list_works_parser.add_argument(
        "--all", action="store_true", help="List all works from all authors"
    )
    list_works_parser.add_argument(
        "--columns",
        type=str,
        help="Comma-separated list of columns (e.g., work_id,title_en). Use 'all' for all fields.",
    )
    list_works_parser.add_argument(
        "--filter",
        action="append",
        dest="filters",
        metavar="FIELD=VALUE",
        help="Filter by field. Use '=' for exact or '~' for contains. Repeatable.",
    )
    list_works_parser.add_argument(
        "--limit", type=int, help="Maximum number of results to show"
    )
    list_works_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of results to skip (for pagination)",
    )
    list_works_parser.set_defaults(func=handle_list_works)

    # Search subcommand
    search_parser = subparsers.add_parser(
        "search", help="Search for works by title or author name"
    )
    search_parser.add_argument("query", help="Search query (case-insensitive)")
    search_parser.set_defaults(func=handle_search)

    # List corpora subcommand
    list_corpora_parser = subparsers.add_parser(
        "list-corpora", help="List all configured corpora"
    )
    list_corpora_parser.add_argument(
        "--details",
        "--verbose",
        dest="details",
        action="store_true",
        help="Show detailed information for each corpus",
    )
    list_corpora_parser.add_argument(
        "--corpus",
        dest="extra_corpora",
        action="append",
        type=Path,
        help="Additional corpus directory to inspect (repeatable)",
    )
    list_corpora_parser.set_defaults(func=handle_list_corpora)

    # Check corpus subcommand
    check_corpus_parser = subparsers.add_parser(
        "check-corpus", help="Run health checks for a corpus"
    )
    check_corpus_parser.add_argument(
        "--corpus",
        dest="target_corpus",
        help="Corpus name to check (defaults to configured default)",
    )
    check_corpus_parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="Quick sampling or full corpus walk",
    )
    check_corpus_parser.add_argument(
        "--sample-percent",
        dest="sample_percent",
        type=float,
        help="Percentage of files to sample in quick mode",
    )
    check_corpus_parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for sampling",
    )
    check_corpus_parser.set_defaults(func=handle_check_corpus)

    # Check for backward compatibility (old-style invocation without subcommand)
    # If first arg looks like a file path (contains / or ends with .xml), insert 'extract'
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        valid_commands = {
            "extract",
            "list-authors",
            "list-works",
            "search",
            "list-corpora",
            "check-corpus",
        }
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
            level=logging.DEBUG, format="[%(levelname)s] %(name)s: %(message)s"
        )
        logger.debug("Debug mode enabled")
    else:
        # WARNING level shows only warnings and errors (not info)
        logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")

    # If no command specified, show help
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Call the appropriate handler
    args.func(args)


if __name__ == "__main__":
    main()
