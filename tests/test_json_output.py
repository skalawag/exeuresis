"""Tests for JSON and JSONL output formats."""

import json

import pytest


class TestJSONWriter:
    """Test suite for JSON output writer."""

    @pytest.fixture
    def sample_segments(self):
        """Sample segment data for testing."""
        return [
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "τί νεώτερον, ὦ Εὐθύφρων, γέγονεν;",
                "stephanus": ["2", "2a"],
                "said_id": 0,
                "is_paragraph_start": True,
                "book": None,
            },
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "οὐδὲν νεώτερον, ὦ Σώκρατες.",
                "stephanus": ["2b"],
                "said_id": 1,
                "is_paragraph_start": False,
                "book": None,
            },
        ]

    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return {
            "work_id": "tlg0059.tlg001",
            "title": "Euthyphro",
            "format_version": "1.0",
        }

    def test_json_format_basic_structure(self, sample_segments, sample_metadata):
        """JSON output should be valid JSON with metadata and segments."""
        from exeuresis.output_writers import JSONWriter

        writer = JSONWriter()
        output = writer.format(sample_segments, metadata=sample_metadata)

        # Parse JSON to verify it's valid
        data = json.loads(output)

        # Check structure
        assert "metadata" in data
        assert "segments" in data
        assert isinstance(data["segments"], list)
        assert len(data["segments"]) == 2

    def test_json_preserves_segment_fields(self, sample_segments):
        """JSON output should preserve all segment fields."""
        from exeuresis.output_writers import JSONWriter

        writer = JSONWriter()
        output = writer.format(sample_segments)
        data = json.loads(output)

        segment = data["segments"][0]
        assert segment["speaker"] == "Σωκράτης"
        assert segment["label"] == "ΣΩ."
        assert segment["text"] == "τί νεώτερον, ὦ Εὐθύφρων, γέγονεν;"
        assert segment["stephanus"] == ["2", "2a"]
        assert segment["said_id"] == 0
        assert segment["is_paragraph_start"] is True
        assert segment["book"] is None

    def test_json_unicode_handling(self, sample_segments):
        """JSON output should handle Greek Unicode correctly."""
        from exeuresis.output_writers import JSONWriter

        writer = JSONWriter()
        output = writer.format(sample_segments)

        # Should use ensure_ascii=False
        assert "Σωκράτης" in output
        assert "Εὐθύφρων" in output
        # Should not be escaped
        assert "\\u" not in output

    def test_json_empty_segments(self):
        """JSON output should handle empty segment list."""
        from exeuresis.output_writers import JSONWriter

        writer = JSONWriter()
        output = writer.format([])
        data = json.loads(output)

        assert data["segments"] == []

    def test_json_metadata_optional(self, sample_segments):
        """JSON output should work without metadata."""
        from exeuresis.output_writers import JSONWriter

        writer = JSONWriter()
        output = writer.format(sample_segments)
        data = json.loads(output)

        assert data["metadata"] == {}
        assert "segments" in data

    def test_json_indentation(self, sample_segments):
        """JSON output should be indented for readability."""
        from exeuresis.output_writers import JSONWriter

        writer = JSONWriter()
        output = writer.format(sample_segments)

        # Check that output is indented (contains multiple spaces)
        assert "  " in output
        # Should have newlines
        assert "\n" in output


class TestJSONLWriter:
    """Test suite for JSONL (newline-delimited JSON) output writer."""

    @pytest.fixture
    def sample_segments(self):
        """Sample segment data for testing."""
        return [
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "First line.",
                "stephanus": ["2a"],
                "said_id": 0,
                "is_paragraph_start": True,
                "book": None,
            },
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "Second line.",
                "stephanus": ["2b"],
                "said_id": 1,
                "is_paragraph_start": False,
                "book": None,
            },
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "Third line.",
                "stephanus": ["2c"],
                "said_id": 2,
                "is_paragraph_start": False,
                "book": "1",
            },
        ]

    def test_jsonl_line_by_line(self, sample_segments):
        """JSONL output should have one JSON object per line."""
        from exeuresis.output_writers import JSONLWriter

        writer = JSONLWriter()
        output = writer.format(sample_segments)

        lines = output.strip().split("\n")
        assert len(lines) == 3

        # Each line should be valid JSON
        for line in lines:
            obj = json.loads(line)
            assert isinstance(obj, dict)

    def test_jsonl_preserves_segment_data(self, sample_segments):
        """JSONL output should preserve all segment fields."""
        from exeuresis.output_writers import JSONLWriter

        writer = JSONLWriter()
        output = writer.format(sample_segments)

        lines = output.strip().split("\n")
        first_segment = json.loads(lines[0])

        assert first_segment["speaker"] == "Σωκράτης"
        assert first_segment["label"] == "ΣΩ."
        assert first_segment["text"] == "First line."
        assert first_segment["stephanus"] == ["2a"]
        assert first_segment["said_id"] == 0
        assert first_segment["is_paragraph_start"] is True

    def test_jsonl_unicode_handling(self, sample_segments):
        """JSONL output should handle Greek Unicode correctly."""
        from exeuresis.output_writers import JSONLWriter

        writer = JSONLWriter()
        output = writer.format(sample_segments)

        # Should use ensure_ascii=False
        assert "Σωκράτης" in output
        assert "Εὐθύφρων" in output
        # Should not be escaped
        assert "\\u" not in output

    def test_jsonl_empty_segments(self):
        """JSONL output should handle empty segment list."""
        from exeuresis.output_writers import JSONLWriter

        writer = JSONLWriter()
        output = writer.format([])

        assert output == ""

    def test_jsonl_no_metadata(self, sample_segments):
        """JSONL format ignores metadata (not applicable)."""
        from exeuresis.output_writers import JSONLWriter

        writer = JSONLWriter()
        metadata = {"work_id": "tlg0059.tlg001"}
        output = writer.format(sample_segments, metadata=metadata)

        # Metadata should not appear in output
        assert "work_id" not in output
        assert "tlg0059.tlg001" not in output

        # Should only contain segment data
        lines = output.strip().split("\n")
        first_segment = json.loads(lines[0])
        assert "text" in first_segment
        assert "metadata" not in first_segment

    def test_jsonl_compact_format(self, sample_segments):
        """JSONL should be compact (no indentation)."""
        from exeuresis.output_writers import JSONLWriter

        writer = JSONLWriter()
        output = writer.format(sample_segments)

        lines = output.strip().split("\n")
        # Each line should not contain indentation (multiple spaces)
        for line in lines:
            # No double spaces (which would indicate indentation)
            assert "  " not in line

    def test_jsonl_book_field_handling(self, sample_segments):
        """JSONL should handle both None and string book values."""
        from exeuresis.output_writers import JSONLWriter

        writer = JSONLWriter()
        output = writer.format(sample_segments)

        lines = output.strip().split("\n")
        first_segment = json.loads(lines[0])
        third_segment = json.loads(lines[2])

        # First segment has book=None
        assert first_segment["book"] is None
        # Third segment has book="1"
        assert third_segment["book"] == "1"


class TestTextWriter:
    """Test suite for TextWriter wrapper (backward compatibility)."""

    @pytest.fixture
    def sample_segments(self):
        """Sample segment data for testing."""
        return [
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "τί νεώτερον;",
                "stephanus": ["2a"],
                "said_id": 0,
                "is_paragraph_start": True,
                "book": None,
            },
        ]

    def test_text_writer_uses_text_formatter(self, sample_segments):
        """TextWriter should delegate to TextFormatter."""
        from exeuresis.formatter import OutputStyle
        from exeuresis.output_writers import TextWriter

        writer = TextWriter(style=OutputStyle.FULL_MODERN, wrap_width=79)
        output = writer.format(sample_segments)

        # Should contain formatted text
        assert isinstance(output, str)
        assert "ΣΩ." in output
        assert "τί νεώτερον;" in output


class TestCLIIntegration:
    """Integration tests for CLI with --format flag."""

    def test_cli_format_flag_json(self, tmp_path):
        """Test CLI with --format json."""
        import subprocess
        import sys

        output_file = tmp_path / "test_output.json"

        # Note: This will fail until CLI is updated, which is expected in TDD
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "exeuresis.cli",
                "extract",
                "canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml",
                "2a-2b",
                "--format",
                "json",
                "-o",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/json-output",
        )

        # Should succeed
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Output file should exist
        assert output_file.exists()

        # Should be valid JSON
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "segments" in data
        assert len(data["segments"]) > 0

    def test_cli_format_flag_jsonl(self, tmp_path):
        """Test CLI with --format jsonl."""
        import subprocess
        import sys

        output_file = tmp_path / "test_output.jsonl"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "exeuresis.cli",
                "extract",
                "canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml",
                "2a-2b",
                "--format",
                "jsonl",
                "-o",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/json-output",
        )

        # Should succeed
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Output file should exist
        assert output_file.exists()

        # Should be valid JSONL (each line is valid JSON)
        with open(output_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) > 0
        for line in lines:
            if line.strip():
                obj = json.loads(line)
                assert "text" in obj

    def test_cli_format_json_to_stdout(self):
        """Test CLI with --format json --print."""
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "exeuresis.cli",
                "extract",
                "canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml",
                "2a",
                "--format",
                "json",
                "--print",
            ],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/json-output",
        )

        assert result.returncode == 0
        # stdout should be valid JSON
        data = json.loads(result.stdout)
        assert "segments" in data

    def test_cli_default_format_is_text(self, tmp_path):
        """Test that default format is still text (backward compatibility)."""
        import subprocess
        import sys

        output_file = tmp_path / "test_output.txt"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "exeuresis.cli",
                "extract",
                "canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc1.xml",
                "2a",
                "-o",
                str(output_file),
            ],
            capture_output=True,
            text=True,
            cwd="/home/mark/vm_share/python/exeuresis/.worktrees/json-output",
        )

        assert result.returncode == 0

        # Should be text format, not JSON
        content = output_file.read_text()
        # Should NOT be valid JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(content)
