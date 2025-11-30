"""Tests for catalog exploration features (columns, filters, pagination)."""

import subprocess
import sys

import pytest

from exeuresis.catalog import PerseusAuthor, PerseusWork
from exeuresis.cli_catalog import (
    filter_authors,
    filter_works,
    format_authors_table,
    format_works_table,
    paginate,
    parse_filter,
)


class TestFilterParsing:
    """Test filter string parsing."""

    def test_parse_filter_exact_match(self):
        """Parse exact match filter."""
        field, op, value = parse_filter("name_en=Plato")
        assert field == "name_en"
        assert op == "="
        assert value == "Plato"

    def test_parse_filter_contains_match(self):
        """Parse contains match filter."""
        field, op, value = parse_filter("name_en~Plat")
        assert field == "name_en"
        assert op == "~"
        assert value == "Plat"

    def test_parse_filter_with_spaces(self):
        """Parse filter with spaces around operators."""
        field, op, value = parse_filter("name_en = Plato")
        assert field == "name_en"
        assert value == "Plato"

    def test_parse_filter_invalid_format(self):
        """Invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid filter format"):
            parse_filter("invalid_format")


class TestAuthorFiltering:
    """Test author filtering logic."""

    @pytest.fixture
    def sample_authors(self):
        return [
            PerseusAuthor("tlg0059", "Plato", "Πλάτων"),
            PerseusAuthor("tlg0012", "Homer", "Ὅμηρος"),
            PerseusAuthor("tlg0003", "Thucydides", ""),
            PerseusAuthor("tlg0014", "Demosthenes", "Δημοσθένης"),
        ]

    def test_filter_authors_exact_match(self, sample_authors):
        """Exact match on name_en field."""
        filtered = filter_authors(sample_authors, filters=[("name_en", "=", "Plato")])
        assert len(filtered) == 1
        assert filtered[0].name_en == "Plato"

    def test_filter_authors_contains_match(self, sample_authors):
        """Contains match with ~ operator."""
        filtered = filter_authors(sample_authors, filters=[("name_en", "~", "o")])
        assert len(filtered) == 3  # Plato, Homer, Demosthenes

    def test_filter_authors_case_insensitive(self, sample_authors):
        """Filters are case-insensitive."""
        filtered = filter_authors(sample_authors, filters=[("name_en", "=", "plato")])
        assert len(filtered) == 1
        assert filtered[0].name_en == "Plato"

    def test_filter_authors_multiple_filters(self, sample_authors):
        """Multiple filters use AND logic."""
        filtered = filter_authors(
            sample_authors,
            filters=[("name_en", "~", "o"), ("tlg_id", "=", "tlg0059")],
        )
        assert len(filtered) == 1
        assert filtered[0].tlg_id == "tlg0059"

    def test_filter_authors_no_matches(self, sample_authors):
        """No matches returns empty list."""
        filtered = filter_authors(
            sample_authors, filters=[("name_en", "=", "Aristotle")]
        )
        assert len(filtered) == 0

    def test_filter_authors_greek_name(self, sample_authors):
        """Can filter by Greek name."""
        filtered = filter_authors(sample_authors, filters=[("name_grc", "~", "Πλάτ")])
        assert len(filtered) == 1
        assert filtered[0].name_en == "Plato"

    def test_filter_authors_invalid_field(self, sample_authors):
        """Invalid field name raises error."""
        with pytest.raises(ValueError, match="Invalid field"):
            filter_authors(sample_authors, filters=[("invalid", "=", "value")])


class TestWorkFiltering:
    """Test work filtering logic."""

    @pytest.fixture
    def sample_works(self):
        return [
            PerseusWork(
                "tlg0059", "tlg001", "Euthyphro", "Εὐθύφρων", page_range="2-16"
            ),
            PerseusWork(
                "tlg0059", "tlg030", "Republic", "Πολιτεία", page_range="327-621"
            ),
            PerseusWork(
                "tlg0059",
                "tlg013",
                "Alcibiades 1",
                "Ἀλκιβιάδης αʹ",
                page_range="103-135",
            ),
            PerseusWork("tlg0012", "tlg001", "Iliad", "Ἰλιάς", page_range="1-24"),
        ]

    def test_filter_works_by_title(self, sample_works):
        """Filter works by title."""
        filtered = filter_works(sample_works, filters=[("title_en", "~", "Republic")])
        assert len(filtered) == 1
        assert filtered[0].title_en == "Republic"

    def test_filter_works_by_tlg_id(self, sample_works):
        """Filter works by author TLG ID."""
        filtered = filter_works(sample_works, filters=[("tlg_id", "=", "tlg0059")])
        assert len(filtered) == 3
        assert all(w.tlg_id == "tlg0059" for w in filtered)

    def test_filter_works_by_work_id(self, sample_works):
        """Filter works by work ID."""
        filtered = filter_works(sample_works, filters=[("work_id", "=", "tlg001")])
        assert len(filtered) == 2  # Euthyphro and Iliad

    def test_filter_works_multiple_criteria(self, sample_works):
        """Multiple filters work together."""
        filtered = filter_works(
            sample_works,
            filters=[("tlg_id", "=", "tlg0059"), ("title_en", "~", "Alc")],
        )
        assert len(filtered) == 1
        assert filtered[0].title_en == "Alcibiades 1"

    def test_filter_works_invalid_field(self, sample_works):
        """Invalid field raises error."""
        with pytest.raises(ValueError, match="Invalid field"):
            filter_works(sample_works, filters=[("bad_field", "=", "value")])


class TestPagination:
    """Test pagination logic."""

    @pytest.fixture
    def sample_list(self):
        return list(range(100))  # 0-99

    def test_paginate_first_page(self, sample_list):
        """Get first page of results."""
        page = paginate(sample_list, limit=10, offset=0)
        assert len(page) == 10
        assert page == list(range(10))

    def test_paginate_second_page(self, sample_list):
        """Get second page of results."""
        page = paginate(sample_list, limit=10, offset=10)
        assert len(page) == 10
        assert page == list(range(10, 20))

    def test_paginate_last_page_partial(self, sample_list):
        """Last page may have fewer items."""
        page = paginate(sample_list, limit=10, offset=95)
        assert len(page) == 5  # 95-99
        assert page == list(range(95, 100))

    def test_paginate_offset_beyond_total(self, sample_list):
        """Offset beyond total returns empty list."""
        page = paginate(sample_list, limit=10, offset=200)
        assert len(page) == 0

    def test_paginate_no_limit(self, sample_list):
        """No limit returns all results from offset."""
        page = paginate(sample_list, limit=None, offset=0)
        assert len(page) == 100

    def test_paginate_with_offset_no_limit(self, sample_list):
        """No limit with offset returns remaining items."""
        page = paginate(sample_list, limit=None, offset=50)
        assert len(page) == 50
        assert page[0] == 50


class TestColumnSelection:
    """Test column selection and table formatting."""

    @pytest.fixture
    def sample_authors(self):
        return [
            PerseusAuthor("tlg0059", "Plato", "Πλάτων"),
            PerseusAuthor("tlg0012", "Homer", "Ὅμηρος"),
        ]

    @pytest.fixture
    def sample_works(self):
        return [
            PerseusWork(
                "tlg0059", "tlg001", "Euthyphro", "Εὐθύφρων", page_range="2-16"
            ),
            PerseusWork(
                "tlg0059", "tlg030", "Republic", "Πολιτεία", page_range="327-621"
            ),
        ]

    def test_format_authors_default_columns(self, sample_authors):
        """Default columns match current output."""
        output = format_authors_table(sample_authors, columns=None)
        # Should include tlg_id, name_en, name_grc in current format
        assert "tlg0059: Plato" in output or "tlg0059" in output
        assert "Plato" in output

    def test_format_authors_custom_columns(self, sample_authors):
        """Select specific columns."""
        output = format_authors_table(sample_authors, columns=["tlg_id", "name_en"])
        # Should show only TLG ID and English name
        assert "Plato" in output
        assert "tlg0059" in output

    def test_format_authors_all_columns(self, sample_authors):
        """Special 'all' value shows all fields."""
        output = format_authors_table(sample_authors, columns=["all"])
        assert "tlg_id" in output.lower() or "tlg0059" in output
        assert "Plato" in output
        assert "Πλάτων" in output

    def test_format_works_custom_columns(self, sample_works):
        """Select specific columns for works."""
        output = format_works_table(sample_works, columns=["work_id", "title_en"])
        # Should be table with selected columns
        assert "Euthyphro" in output
        assert "Republic" in output
        assert "tlg001" in output

    def test_format_authors_invalid_column(self, sample_authors):
        """Invalid column name raises error."""
        with pytest.raises(ValueError, match="Invalid column"):
            format_authors_table(sample_authors, columns=["invalid_field"])

    def test_format_works_invalid_column(self, sample_works):
        """Invalid column name raises error."""
        with pytest.raises(ValueError, match="Invalid column"):
            format_works_table(sample_works, columns=["bad_column"])

    def test_format_authors_preserves_order(self, sample_authors):
        """Column order is preserved."""
        output = format_authors_table(sample_authors, columns=["name_en", "tlg_id"])
        lines = output.strip().split("\n")
        header = lines[0].lower()
        # name_en should appear before tlg_id in header
        name_pos = header.find("name") if "name" in header else header.find("english")
        id_pos = header.find("tlg") if "tlg" in header else header.find("id")
        assert name_pos < id_pos


class TestCLIIntegration:
    """Integration tests for CLI with new flags."""

    @pytest.fixture
    def cli_command(self):
        return [sys.executable, "-m", "exeuresis.cli"]

    def test_cli_list_authors_with_columns(self, cli_command):
        """Test --columns flag for list-authors."""
        result = subprocess.run(
            cli_command + ["list-authors", "--columns", "tlg_id,name_en"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        assert "tlg0059" in result.stdout
        assert "Plato" in result.stdout

    def test_cli_list_authors_with_filter(self, cli_command):
        """Test --filter flag for list-authors."""
        result = subprocess.run(
            cli_command + ["list-authors", "--filter", "name_en=Plato"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        assert "Plato" in result.stdout
        # Should show filtered count
        assert "1" in result.stdout and (
            "99" in result.stdout or "authors" in result.stdout
        )

    def test_cli_list_authors_with_contains_filter(self, cli_command):
        """Test contains filter with ~ operator."""
        result = subprocess.run(
            cli_command + ["list-authors", "--filter", "name_en~Plat"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        assert "Plato" in result.stdout

    def test_cli_list_authors_with_limit(self, cli_command):
        """Test --limit flag for list-authors."""
        result = subprocess.run(
            cli_command + ["list-authors", "--limit", "5"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        # Should show pagination info
        assert (
            "1-5 of" in result.stdout
            or "Showing 5" in result.stdout
            or "Showing 1-5" in result.stdout
        )

    def test_cli_list_authors_with_offset(self, cli_command):
        """Test --offset flag for list-authors."""
        result = subprocess.run(
            cli_command + ["list-authors", "--limit", "5", "--offset", "10"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        # Should show pagination starting from 11
        assert "11-15" in result.stdout or "Showing" in result.stdout

    def test_cli_list_works_with_filter(self, cli_command):
        """Test --filter flag for list-works."""
        result = subprocess.run(
            cli_command + ["list-works", "--all", "--filter", "title_en~Republic"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        assert "Republic" in result.stdout

    def test_cli_list_works_with_columns(self, cli_command):
        """Test --columns flag for list-works."""
        result = subprocess.run(
            cli_command + ["list-works", "tlg0059", "--columns", "work_id,title_en"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        assert "Euthyphro" in result.stdout

    def test_cli_combined_flags(self, cli_command):
        """Test combining multiple flags."""
        result = subprocess.run(
            cli_command
            + [
                "list-works",
                "--all",
                "--filter",
                "tlg_id=tlg0059",
                "--columns",
                "work_id,title_en",
                "--limit",
                "10",
            ],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        # Should have Plato's works, limited to 10
        assert "Showing" in result.stdout or "10" in result.stdout

    def test_cli_multiple_filters(self, cli_command):
        """Test multiple --filter flags."""
        result = subprocess.run(
            cli_command
            + [
                "list-works",
                "--all",
                "--filter",
                "tlg_id=tlg0059",
                "--filter",
                "title_en~Alc",
            ],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        assert "Alcibiades" in result.stdout

    def test_cli_backward_compatibility_list_authors(self, cli_command):
        """Test that old commands still work unchanged."""
        result = subprocess.run(
            cli_command + ["list-authors"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        assert "Found 99 authors" in result.stdout or "authors" in result.stdout
        assert "tlg0059" in result.stdout
        assert "Plato" in result.stdout

    def test_cli_backward_compatibility_list_works(self, cli_command):
        """Test that old list-works command still works."""
        result = subprocess.run(
            cli_command + ["list-works", "tlg0059"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode == 0
        assert "Found 36 works" in result.stdout or "works" in result.stdout
        assert "Euthyphro" in result.stdout

    def test_cli_invalid_filter_format(self, cli_command):
        """Test error handling for invalid filter format."""
        result = subprocess.run(
            cli_command + ["list-authors", "--filter", "invalid_format"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode != 0
        assert "Invalid filter" in result.stderr or "format" in result.stderr.lower()

    def test_cli_invalid_column(self, cli_command):
        """Test error handling for invalid column name."""
        result = subprocess.run(
            cli_command + ["list-authors", "--columns", "invalid_column"],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/catalog-exploration",
        )

        assert result.returncode != 0
        assert "Invalid column" in result.stderr or "invalid" in result.stderr.lower()
