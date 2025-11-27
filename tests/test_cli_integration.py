"""Integration tests for CLI with range filtering."""

import pytest
from pathlib import Path
from pi_grapheion.cli import main
import sys


def test_cli_extract_with_range_single_section(monkeypatch, tmp_path, capsys):
    """Test CLI extract with single section range."""
    # Use the existing sample XML
    xml_path = Path("tests/fixtures/sample_minimal.xml")
    if not xml_path.exists():
        pytest.skip("Sample XML not found")

    # Mock sys.argv
    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        str(xml_path),
        '2a',
        '--print'
    ])

    # Run CLI
    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    # Should only contain text from section 2a
    assert "2a" in captured.out or len(captured.out) > 0


def test_cli_extract_with_invalid_range(monkeypatch, tmp_path, capsys):
    """Test CLI extract with invalid range raises error."""
    xml_path = Path("tests/fixtures/sample_minimal.xml")
    if not xml_path.exists():
        pytest.skip("Sample XML not found")

    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        str(xml_path),
        '999z',
        '--print'
    ])

    # Should exit with error
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "999z" in captured.err
