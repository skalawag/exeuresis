"""Tests for Stephanus pagination formatting and text wrapping."""

import pytest
from pi_grapheion.formatter import TextFormatter, OutputStyle


class TestStephanusFormatting:
    """Test suite for Stephanus pagination formatting rules."""

    def test_first_section_shows_page_number_only(self):
        """First section (e.g., 2a) should display as [2]."""
        dialogue_data = [
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "First section text",
                "stephanus": ["2", "2a"],
            }
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should show [2] for the first section (2a)
        assert "[2]" in output
        # Should NOT show [2a] or [a]
        assert "[2a]" not in output
        assert "[a]" not in output

    def test_subsequent_sections_show_letter_only_with_context(self):
        """Subsequent sections (e.g., 2b, 2c) should display as [b], [c] when page already shown."""
        dialogue_data = [
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "First section text",
                "stephanus": ["2", "2a"],
            },
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "Second section text",
                "stephanus": ["2b"],
            },
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "Third section text",
                "stephanus": ["2c"],
            },
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should show [2] for first section
        assert "[2]" in output
        # Should show [b] and [c] for subsequent sections
        assert "[b]" in output
        assert "[c]" in output
        # Should NOT show full references
        assert "[2b]" not in output
        assert "[2c]" not in output

    def test_subsequent_section_without_prior_context_shows_letter(self):
        """Subsequent sections (e.g., 2b) without prior page context should still show letter."""
        dialogue_data = [
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "Second section text",
                "stephanus": ["2b"],
            },
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "Third section text",
                "stephanus": ["2c"],
            },
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should show [b] and [c] (subsequent sections always show letter only)
        assert "[b]" in output
        assert "[c]" in output
        # Should NOT show full references
        assert "[2b]" not in output
        assert "[2c]" not in output

    def test_mixed_sections_formatting(self):
        """Test a mix of first and subsequent sections."""
        dialogue_data = [
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "Page 2 section a",
                "stephanus": ["2", "2a"],
            },
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "Page 2 section b",
                "stephanus": ["2b"],
            },
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "Page 3 section a",
                "stephanus": ["3", "3a"],
            },
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "Page 3 section b",
                "stephanus": ["3b"],
            },
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should show [2] for first section of page 2
        assert "[2]" in output
        # Should show letters only for subsequent sections
        assert "[b]" in output
        # Should show [3] for first section of page 3
        assert "[3]" in output

    def test_multiple_markers_in_single_entry(self):
        """Test entry with multiple Stephanus markers (e.g., ['58b', '58c'])."""
        dialogue_data = [
            {
                "speaker": "Φαίδων",
                "label": "ΦΑΙΔ.",
                "text": "Page 58 section a",
                "stephanus": ["58", "58a"],
            },
            {
                "speaker": "Ἐχεκράτης",
                "label": "ΕΧ.",
                "text": "Page 58 sections b and c",
                "stephanus": ["58b", "58c"],
            },
            {
                "speaker": "Φαίδων",
                "label": "ΦΑΙΔ.",
                "text": "Page 58 section d",
                "stephanus": ["58d"],
            },
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should show [58] for first section
        assert "[58]" in output
        # Should show [b] for the first marker in the multiple-marker entry
        assert "[b]" in output
        # Should NOT show [58b] or [58c]
        assert "[58b]" not in output
        assert "[58c]" not in output
        # Should show [d]
        assert "[d]" in output

    def test_single_digit_page_marker(self):
        """Test single digit page number (e.g., ['2'])."""
        dialogue_data = [
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "Page 2 text",
                "stephanus": ["2"],
            },
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should show [2]
        assert "[2]" in output

    def test_page_transition(self):
        """Test transition from one page to another."""
        dialogue_data = [
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "Page 2 section a",
                "stephanus": ["2", "2a"],
            },
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "Page 2 section e (last section)",
                "stephanus": ["2e"],
            },
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "Page 3 section a (new page)",
                "stephanus": ["3", "3a"],
            },
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "Page 3 section b",
                "stephanus": ["3b"],
            },
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should show page numbers for first sections
        assert "[2]" in output
        assert "[3]" in output
        # Should show letters for subsequent sections
        assert "[e]" in output
        assert "[b]" in output
        # Count occurrences to ensure [b] appears once (not [2b])
        assert output.count("[b]") == 1

    def test_first_section_a_without_page_number(self):
        """Test when first section is '59a' without preceding '59'."""
        dialogue_data = [
            {
                "speaker": "Φαίδων",
                "label": "ΦΑΙΔ.",
                "text": "First section of page 59",
                "stephanus": ["59a"],
            },
            {
                "speaker": "Ἐχεκράτης",
                "label": "ΕΧ.",
                "text": "Second section of page 59",
                "stephanus": ["59b"],
            },
            {
                "speaker": "Φαίδων",
                "label": "ΦΑΙΔ.",
                "text": "Third section of page 59",
                "stephanus": ["59c"],
            },
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should show [59] for first section (59a)
        assert "[59]" in output
        # Should show [b] and [c] for subsequent sections
        assert "[b]" in output
        assert "[c]" in output
        # Should NOT show [59a], [59b], [59c]
        assert "[59a]" not in output
        assert "[59b]" not in output
        assert "[59c]" not in output

    def test_real_phaedo_structure_pages_59_to_62(self):
        """Test the actual structure from Phaedo pages 59-62."""
        dialogue_data = [
            {"speaker": "", "label": "", "text": "Text before 59", "stephanus": []},
            {"speaker": "", "label": "", "text": "Page 59a text", "stephanus": ["59a"]},
            {"speaker": "", "label": "", "text": "Page 59b text", "stephanus": ["59b"]},
            {"speaker": "", "label": "", "text": "More text", "stephanus": []},
            {"speaker": "", "label": "", "text": "Page 59c text", "stephanus": ["59c"]},
            {"speaker": "", "label": "", "text": "Page 59e text", "stephanus": ["59e"]},
            {"speaker": "", "label": "", "text": "Page 60 all sections", "stephanus": ["60a", "60b", "60c", "60d", "60e"]},
            {"speaker": "", "label": "", "text": "Page 61 all sections", "stephanus": ["61a", "61b", "61c", "61d", "61e"]},
            {"speaker": "", "label": "", "text": "Page 62 all sections", "stephanus": ["62a", "62b", "62c", "62d", "62e"]},
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # All page numbers should appear
        assert "[59]" in output, "Page 59 marker should appear for 59a"
        assert "[60]" in output, "Page 60 marker should appear for 60a"
        assert "[61]" in output, "Page 61 marker should appear for 61a"
        assert "[62]" in output, "Page 62 marker should appear for 62a"

        # Section letters should appear
        assert "[b]" in output
        assert "[c]" in output
        assert "[e]" in output


class TestTextWrapping:
    """Test suite for text wrapping and paragraph formatting."""

    def test_text_wrapped_at_79_chars(self):
        """Text should be wrapped at 79 characters per line."""
        # Create dialogue with long text
        long_text = (
            "τί νεώτερον ὦ Σώκρατες γέγονεν ὅτι σὺ τὰς ἐν Λυκείῳ καταλιπὼν "
            "διατριβὰς ἐνθάδε νῦν διατρίβεις περὶ τὴν τοῦ βασιλέως στοάν"
        )

        dialogue_data = [
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": long_text,
                "stephanus": ["2", "2a"],
            }
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        lines = output.split("\n")
        for line in lines:
            if line.strip():  # Skip empty lines
                assert len(line) <= 79, f"Line exceeds 79 chars: {len(line)} chars"

    def test_paragraphs_separated_by_empty_line(self):
        """Paragraphs (one per <said> element) should be separated by empty lines."""
        dialogue_data = [
            # First <said> element with two milestone segments
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "First said element first segment",
                "stephanus": ["2", "2a"],
                "said_id": 0,
            },
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "First said element second segment (same paragraph)",
                "stephanus": ["2b"],
                "said_id": 0,
            },
            # Second <said> element
            {
                "speaker": "Σωκράτης",
                "label": "ΣΩ.",
                "text": "Second said element (new paragraph)",
                "stephanus": [],
                "said_id": 1,
            },
            # Third <said> element (back to first speaker)
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "Third said element (new paragraph)",
                "stephanus": ["2c"],
                "said_id": 2,
            },
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        # Should have double newlines between <said> elements (paragraphs)
        # There should be 2 paragraph breaks: said_id 0->1 and 1->2
        assert output.count("\n\n") == 2

        # First <said> element's segments should be in same paragraph
        assert "[2]" in output and "[b]" in output
        lines = output.split("\n\n")
        # First paragraph should contain both [2] and [b]
        assert "[2]" in lines[0] and "[b]" in lines[0]

    def test_wrapped_text_preserves_words(self):
        """Wrapping should not break words in the middle."""
        dialogue_data = [
            {
                "speaker": "Εὐθύφρων",
                "label": "ΕΥΘ.",
                "text": "word1 word2 word3 " * 20,  # Create long text
                "stephanus": ["2", "2a"],
            }
        ]

        formatter = TextFormatter(dialogue_data)
        output = formatter.format(OutputStyle.FULL_MODERN)

        lines = output.split("\n")
        for line in lines:
            # No line should end with a partial word (crude check)
            # In proper wrapping, we shouldn't see hanging spaces at line end
            if line.strip():
                assert not line.rstrip().endswith(" word")
