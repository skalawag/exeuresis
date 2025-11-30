"""Catalog exploration utilities for CLI."""

from typing import List, Optional, Tuple

from exeuresis.catalog import PerseusAuthor, PerseusWork


def parse_filter(filter_str: str) -> Tuple[str, str, str]:
    """
    Parse filter string like 'field=value' or 'field~value'.

    Args:
        filter_str: Filter string (e.g., "name_en=Plato" or "title~Rep")

    Returns:
        Tuple of (field, operator, value)

    Raises:
        ValueError: If filter format is invalid
    """
    if "~" in filter_str:
        field, value = filter_str.split("~", 1)
        return (field.strip(), "~", value.strip())
    elif "=" in filter_str:
        field, value = filter_str.split("=", 1)
        return (field.strip(), "=", value.strip())
    else:
        raise ValueError(
            f"Invalid filter format: '{filter_str}'. "
            "Use 'field=value' for exact match or 'field~value' for contains."
        )


def filter_authors(
    authors: List[PerseusAuthor], filters: List[Tuple[str, str, str]]
) -> List[PerseusAuthor]:
    """
    Apply filters to author list.

    Args:
        authors: List of PerseusAuthor objects
        filters: List of (field, operator, value) tuples

    Returns:
        Filtered list of authors

    Raises:
        ValueError: If field name is invalid
    """
    # Validate field names
    valid_fields = {"tlg_id", "name_en", "name_grc"}
    for field, op, value in filters:
        if field not in valid_fields:
            raise ValueError(
                f"Invalid field: '{field}'. Valid fields: {', '.join(sorted(valid_fields))}"
            )

    # Apply filters (AND logic)
    result = authors
    for field, op, value in filters:
        value_lower = value.lower()
        if op == "=":
            # Exact match (case-insensitive)
            result = [a for a in result if getattr(a, field).lower() == value_lower]
        elif op == "~":
            # Contains match (case-insensitive)
            result = [a for a in result if value_lower in getattr(a, field).lower()]

    return result


def filter_works(
    works: List[PerseusWork], filters: List[Tuple[str, str, str]]
) -> List[PerseusWork]:
    """
    Apply filters to work list.

    Args:
        works: List of PerseusWork objects
        filters: List of (field, operator, value) tuples

    Returns:
        Filtered list of works

    Raises:
        ValueError: If field name is invalid
    """
    # Validate field names
    valid_fields = {"tlg_id", "work_id", "title_en", "title_grc", "page_range"}
    for field, op, value in filters:
        if field not in valid_fields:
            raise ValueError(
                f"Invalid field: '{field}'. Valid fields: {', '.join(sorted(valid_fields))}"
            )

    # Apply filters (AND logic)
    result = works
    for field, op, value in filters:
        value_lower = value.lower()
        if op == "=":
            # Exact match (case-insensitive)
            result = [w for w in result if getattr(w, field).lower() == value_lower]
        elif op == "~":
            # Contains match (case-insensitive)
            result = [w for w in result if value_lower in getattr(w, field).lower()]

    return result


def paginate(items: List, limit: Optional[int] = None, offset: int = 0) -> List:
    """
    Apply pagination to list.

    Args:
        items: List of items to paginate
        limit: Maximum number of items to return (None = no limit)
        offset: Number of items to skip

    Returns:
        Paginated list
    """
    if limit is None:
        return items[offset:]
    return items[offset : offset + limit]


def format_authors_table(
    authors: List[PerseusAuthor], columns: Optional[List[str]] = None
) -> str:
    """
    Format authors as table with selected columns.

    Args:
        authors: List of PerseusAuthor objects
        columns: List of column names, None for default, ["all"] for all columns

    Returns:
        Formatted table string

    Raises:
        ValueError: If column name is invalid
    """
    if not authors:
        return ""

    # Default columns for backward compatibility
    if columns is None:
        # Use current format: "tlg0059: Plato (Greek name)"
        lines = []
        for author in authors:
            if author.name_grc:
                lines.append(f"{author.tlg_id}: {author.name_en} ({author.name_grc})")
            else:
                lines.append(f"{author.tlg_id}: {author.name_en}")
        return "\n".join(lines)

    # Handle 'all' special value
    if columns == ["all"]:
        columns = ["tlg_id", "name_en", "name_grc"]

    # Validate columns
    valid_columns = {"tlg_id", "name_en", "name_grc"}
    for col in columns:
        if col not in valid_columns:
            raise ValueError(
                f"Invalid column: '{col}'. Valid columns: {', '.join(sorted(valid_columns))}"
            )

    # Build table header
    header_names = {
        "tlg_id": "TLG ID",
        "name_en": "Name (English)",
        "name_grc": "Name (Greek)",
    }

    # Calculate column widths
    col_widths = {}
    for col in columns:
        # Start with header width
        col_widths[col] = len(header_names[col])
        # Check data widths
        for author in authors:
            value = str(getattr(author, col))
            col_widths[col] = max(col_widths[col], len(value))

    # Build header
    header_parts = [header_names[col].ljust(col_widths[col]) for col in columns]
    header = "  ".join(header_parts)
    separator = "-" * len(header)

    # Build rows
    rows = []
    for author in authors:
        row_parts = [
            str(getattr(author, col)).ljust(col_widths[col]) for col in columns
        ]
        rows.append("  ".join(row_parts))

    return "\n".join([header, separator] + rows)


def format_works_table(
    works: List[PerseusWork], columns: Optional[List[str]] = None
) -> str:
    """
    Format works as table with selected columns.

    Args:
        works: List of PerseusWork objects
        columns: List of column names, None for default, ["all"] for all columns

    Returns:
        Formatted table string, or None for default (use legacy formatting)

    Raises:
        ValueError: If column name is invalid
    """
    if not works:
        return ""

    # Default columns for backward compatibility - use existing _print_works_table
    if columns is None:
        # Return signal to use legacy formatting
        return None

    # Handle 'all' special value
    if columns == ["all"]:
        columns = ["tlg_id", "work_id", "title_en", "title_grc", "page_range"]

    # Validate columns
    valid_columns = {"tlg_id", "work_id", "title_en", "title_grc", "page_range"}
    for col in columns:
        if col not in valid_columns:
            raise ValueError(
                f"Invalid column: '{col}'. Valid columns: {', '.join(sorted(valid_columns))}"
            )

    # Build table header
    header_names = {
        "tlg_id": "Author ID",
        "work_id": "Work ID",
        "title_en": "Title (English)",
        "title_grc": "Title (Greek)",
        "page_range": "Page Range",
    }

    # Calculate column widths
    col_widths = {}
    for col in columns:
        col_widths[col] = len(header_names[col])
        for work in works:
            value = str(getattr(work, col) or "")
            col_widths[col] = max(col_widths[col], len(value))

    # Build header
    header_parts = [header_names[col].ljust(col_widths[col]) for col in columns]
    header = "  ".join(header_parts)
    separator = "-" * len(header)

    # Build rows
    rows = []
    for work in works:
        row_parts = []
        for col in columns:
            value = str(getattr(work, col) or "")
            row_parts.append(value.ljust(col_widths[col]))
        rows.append("  ".join(row_parts))

    return "\n".join([header, separator] + rows)
