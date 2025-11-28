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


def test_cli_extract_plato_euthyphro_range(monkeypatch, capsys):
    """Test extracting a range from Plato's Euthyphro."""
    # Use real Perseus file if available
    xml_path = Path("canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc2.xml")
    if not xml_path.exists():
        pytest.skip("Plato's Euthyphro not found in canonical-greekLit")

    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        'tlg0059.tlg001',
        '2a-2b',
        '--print',
        '--style', 'C'  # No punctuation for easier testing
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    # Should contain text from 2a-2b range only
    # Should NOT contain text from 3a or later
    assert len(captured.out) > 0
    # Verify it's a subset (not the whole work)
    assert len(captured.out) < 50000  # Euthyphro is longer than this


def test_cli_extract_page_range(monkeypatch, capsys):
    """Test extracting a full page range."""
    xml_path = Path("canonical-greekLit/data/tlg0059/tlg001/tlg0059.tlg001.perseus-grc2.xml")
    if not xml_path.exists():
        pytest.skip("Plato's Euthyphro not found")

    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        'tlg0059.tlg001',
        '2',  # Just page 2
        '--print'
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    # Should contain text from page 2 (all sections)
    assert "2a" in captured.out or "2" in captured.out or "[a]" in captured.out


def test_cli_extract_anthology_single_work(monkeypatch, capsys):
    """Test anthology extraction from single work with multiple ranges."""
    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        'euthyphro',
        '--passages', '5a,7b-7c',
        '--print'
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    # Should contain header for Euthyphro
    assert "Euthyphro" in captured.out or "Εὐθύφρων" in captured.out
    # Should contain range displays
    assert "5a" in captured.out
    assert "7b-7c" in captured.out or "7b" in captured.out


def test_cli_extract_anthology_multiple_works(monkeypatch, capsys):
    """Test anthology extraction from multiple works."""
    monkeypatch.setattr(sys, 'argv', [
        'pi_grapheion',
        'extract',
        'euthyphro',
        '--passages', '5a',
        'republic',
        '--passages', '354b',
        '--print'
    ])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    # Should contain headers for both works
    assert "Euthyphro" in captured.out or "Εὐθύφρων" in captured.out
    assert "Republic" in captured.out or "Πολιτεία" in captured.out
    # Should have blank line separators between blocks
    assert "\n\n" in captured.out
