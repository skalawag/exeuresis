"""Tests for CLI functionality."""

import pytest
from pathlib import Path
import subprocess
import sys


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def cli_command(self):
        """Base CLI command."""
        return [sys.executable, "-m", "exeuresis.cli"]

    @pytest.fixture
    def euthyphro_xml(self):
        """Path to Euthyphro test file."""
        return Path("canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml")

    def test_list_authors(self, cli_command):
        """Test list-authors command."""
        result = subprocess.run(
            cli_command + ["list-authors"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Found" in result.stdout
        assert "authors" in result.stdout
        assert "Plato" in result.stdout or "tlg0059" in result.stdout

    def test_list_works_plato(self, cli_command):
        """Test list-works command for Plato."""
        result = subprocess.run(
            cli_command + ["list-works", "tlg0059"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Plato" in result.stdout
        assert "Euthyphro" in result.stdout or "tlg001" in result.stdout

    def test_list_works_by_author_name(self, cli_command):
        """Test list-works command with author name instead of TLG ID."""
        result = subprocess.run(
            cli_command + ["list-works", "Plato"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Plato" in result.stdout
        assert "Euthyphro" in result.stdout
        # Check that page ranges are included
        assert "[2-16]" in result.stdout  # Euthyphro's page range

    def test_list_works_by_author_name_lowercase(self, cli_command):
        """Test list-works with lowercase author name."""
        result = subprocess.run(
            cli_command + ["list-works", "plato"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Plato" in result.stdout

    def test_list_works_invalid_author(self, cli_command):
        """Test list-works with invalid author ID."""
        result = subprocess.run(
            cli_command + ["list-works", "tlg9999"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        assert "not found" in result.stderr.lower()

    def test_search_by_title(self, cli_command):
        """Test search command by title."""
        result = subprocess.run(
            cli_command + ["search", "Euthyphro"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Euthyphro" in result.stdout
        assert "tlg0059" in result.stdout

    def test_search_by_author(self, cli_command):
        """Test search command by author name."""
        result = subprocess.run(
            cli_command + ["search", "Plato"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Plato" in result.stdout or "tlg0059" in result.stdout
        # Should find multiple works
        assert "Found" in result.stdout

    def test_search_no_results(self, cli_command):
        """Test search with no results."""
        result = subprocess.run(
            cli_command + ["search", "NonexistentWork123"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "No results found" in result.stderr or "0 matches" in result.stdout

    def test_extract_by_work_id(self, cli_command, tmp_path):
        """Test extract command with work ID."""
        output_file = tmp_path / "test_output.txt"

        result = subprocess.run(
            cli_command + ["extract", "tlg0059.tlg001", "--output", str(output_file)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert "ΕΥΘΥΦΡΩΝ" in content  # Title should be present

    def test_extract_by_file_path(self, cli_command, euthyphro_xml, tmp_path):
        """Test extract command with file path."""
        if not euthyphro_xml.exists():
            pytest.skip("Euthyphro XML file not available")

        output_file = tmp_path / "test_output.txt"

        result = subprocess.run(
            cli_command + ["extract", str(euthyphro_xml), "--output", str(output_file)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_extract_with_print_flag(self, cli_command):
        """Test extract with --print flag outputs to stdout."""
        result = subprocess.run(
            cli_command + ["extract", "tlg0059.tlg001", "--print"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert len(result.stdout) > 0
        assert "ΕΥΘΥΦΡΩΝ" in result.stdout

    def test_extract_invalid_work_id(self, cli_command):
        """Test extract with invalid work ID."""
        result = subprocess.run(
            cli_command + ["extract", "tlg9999.tlg999", "--print"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        assert "not found" in result.stderr.lower()

    def test_extract_with_style_option(self, cli_command, tmp_path):
        """Test extract with different style option."""
        output_file = tmp_path / "test_output_styled.txt"

        result = subprocess.run(
            cli_command + ["extract", "tlg0059.tlg001", "--style", "D", "--output", str(output_file)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert output_file.exists()

    def test_extract_with_verbose_flag(self, cli_command):
        """Test extract with verbose flag."""
        result = subprocess.run(
            cli_command + ["extract", "tlg0059.tlg001", "--print", "--verbose"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        # Verbose output goes to stderr
        assert "Processing:" in result.stderr or "Parsing" in result.stderr

    def test_debug_flag(self, cli_command):
        """Test --debug global flag."""
        result = subprocess.run(
            cli_command + ["--debug", "list-authors"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Debug mode enabled" in result.stderr or "[DEBUG]" in result.stderr

    def test_help_output(self, cli_command):
        """Test --help shows usage information."""
        result = subprocess.run(
            cli_command + ["--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "extract" in result.stdout
        assert "list-authors" in result.stdout
        assert "search" in result.stdout

    def test_no_command_shows_help(self, cli_command):
        """Test running with no command shows help."""
        result = subprocess.run(
            cli_command,
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        assert "usage:" in result.stdout.lower()

    def test_backward_compatibility_old_style(self, cli_command, tmp_path):
        """Test backward compatibility with old-style invocation."""
        output_file = tmp_path / "test_old_style.txt"

        # Old style: python -m src.cli <file> without 'extract' subcommand
        result = subprocess.run(
            cli_command + ["canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml",
                          "--output", str(output_file)],
            capture_output=True,
            text=True
        )

        # Should work via backward compatibility
        if Path("canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml").exists():
            assert result.returncode == 0
            assert output_file.exists()

    def test_extract_by_work_name_alias(self, cli_command):
        """Test extract command with work name alias (e.g., 'euthyphro')."""
        result = subprocess.run(
            cli_command + ["extract", "euthyphro", "--print"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert len(result.stdout) > 0
        assert "ΕΥΘΥΦΡΩΝ" in result.stdout

    def test_extract_work_id_and_alias_produce_same_output(self, cli_command):
        """Test that work ID and work name alias produce identical output."""
        # Extract using work ID
        result_id = subprocess.run(
            cli_command + ["extract", "tlg0059.tlg001", "--print"],
            capture_output=True,
            text=True
        )

        # Extract using work name alias
        result_alias = subprocess.run(
            cli_command + ["extract", "euthyphro", "--print"],
            capture_output=True,
            text=True
        )

        assert result_id.returncode == 0
        assert result_alias.returncode == 0
        assert result_id.stdout == result_alias.stdout
