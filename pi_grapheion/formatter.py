"""Text formatting for different output styles."""

from enum import Enum
from typing import List, Dict
import re
import textwrap
import unicodedata


class OutputStyle(Enum):
    """Available output formatting styles."""

    FULL_MODERN = "full_modern"  # Style A
    MINIMAL_PUNCTUATION = "minimal_punctuation"  # Style B
    NO_PUNCTUATION = "no_punctuation"  # Style C
    NO_PUNCTUATION_NO_LABELS = "no_punctuation_no_labels"  # Style D
    SCRIPTIO_CONTINUA = "scriptio_continua"  # Style E
    CUSTOM = "custom"  # Style F
    STEPHANUS_LAYOUT = "stephanus_layout"  # Style S


class TextFormatter:
    """Formats extracted dialogue text according to different styles."""

    def __init__(self, dialogue_data: List[Dict[str, any]], extractor=None, parser=None):
        """
        Initialize formatter with dialogue data.

        Args:
            dialogue_data: List of dialogue dictionaries from TextExtractor
            extractor: Optional TextExtractor instance for Style G re-extraction
            parser: Optional TEIParser instance for accessing title and metadata
        """
        # Store original dialogue data (Style A uses this as-is)
        self.dialogue_data = dialogue_data
        self.extractor = extractor
        self.parser = parser

        # Extract title if parser provided
        self.title = parser.get_title() if parser else ""

    def _normalize_dashes(self, dialogue_data: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Replace m-dashes with spaces in dialogue text.

        Args:
            dialogue_data: Original dialogue data

        Returns:
            Dialogue data with m-dashes replaced by spaces
        """
        normalized = []
        for entry in dialogue_data:
            normalized_entry = entry.copy()
            # Replace m-dash with space
            normalized_entry["text"] = entry["text"].replace("—", " ")
            # Normalize multiple spaces to single space
            normalized_entry["text"] = " ".join(normalized_entry["text"].split())
            normalized.append(normalized_entry)
        return normalized

    def format(self, style: OutputStyle) -> str:
        """
        Format the dialogue according to the specified style.

        Args:
            style: The OutputStyle to apply

        Returns:
            Formatted text as a string
        """
        if style == OutputStyle.FULL_MODERN:
            return self._format_full_modern()
        elif style == OutputStyle.MINIMAL_PUNCTUATION:
            return self._format_minimal_punctuation()
        elif style == OutputStyle.NO_PUNCTUATION:
            return self._format_no_punctuation()
        elif style == OutputStyle.NO_PUNCTUATION_NO_LABELS:
            return self._format_no_punctuation_no_labels()
        elif style == OutputStyle.SCRIPTIO_CONTINUA:
            return self._format_scriptio_continua()
        elif style == OutputStyle.STEPHANUS_LAYOUT:
            return self._format_stephanus_layout()
        else:
            raise NotImplementedError(f"Style {style} not yet implemented")

    def _format_full_modern(self) -> str:
        """
        Format as Style A: Full modern edition.

        Preserves:
        - Title at top
        - Book headers (e.g., "ΒΙΒΛΙΟΝ Α") for multi-book works
        - All punctuation
        - Speaker labels (only when speaker changes)
        - Stephanus pagination markers (simplified format)
        - Text wrapped at 79 characters
        - Paragraphs separated by empty lines (one paragraph per <said> element)
        """
        if not self.dialogue_data:
            return ""

        # Build paragraphs (one per <said> element)
        paragraphs = []
        current_paragraph_parts = []
        last_page_num = None
        last_speaker = None
        last_said_id = None
        last_book = None

        # Add title at the top if available (in uppercase without accents)
        if self.title:
            paragraphs.append(self._remove_accents(self.title.upper()))

        for entry in self.dialogue_data:
            current_book = entry.get("book", "")

            # Add book header if we've entered a new book
            if current_book and current_book != last_book:
                # Finish current paragraph before adding book header
                if current_paragraph_parts:
                    paragraph_text = " ".join(current_paragraph_parts)
                    wrapped_lines = textwrap.wrap(
                        paragraph_text, width=79, break_long_words=False, break_on_hyphens=False
                    )
                    paragraphs.append("\n".join(wrapped_lines))
                    current_paragraph_parts = []

                # Add book header
                book_header = self._format_book_header(current_book)
                paragraphs.append(book_header)
                last_book = current_book
            current_speaker = entry["speaker"]
            current_said_id = entry.get("said_id")
            is_paragraph_start = entry.get("is_paragraph_start", False)

            # Start new paragraph if:
            # 1. We're in a different <said> element, OR
            # 2. This entry is marked as a paragraph start (from <milestone unit="para"/>)
            if (current_said_id != last_said_id and last_said_id is not None) or is_paragraph_start:
                # Finish current paragraph
                if current_paragraph_parts:
                    paragraph_text = " ".join(current_paragraph_parts)
                    wrapped_lines = textwrap.wrap(
                        paragraph_text, width=79, break_long_words=False, break_on_hyphens=False
                    )
                    paragraphs.append("\n".join(wrapped_lines))
                    current_paragraph_parts = []

            line_parts = []

            # Add Stephanus markers with simplified formatting
            if entry["stephanus"]:
                stephanus_marker = self._format_stephanus_with_context(
                    entry["stephanus"], last_page_num
                )
                if stephanus_marker:
                    line_parts.append(stephanus_marker)
                    last_page_num = self._extract_page_number(entry["stephanus"])

            # Add speaker label only if speaker changed
            if entry["label"] and current_speaker != last_speaker:
                line_parts.append(entry["label"])

            # Add the text
            line_parts.append(entry["text"])

            current_paragraph_parts.append(" ".join(line_parts))
            last_speaker = current_speaker
            last_said_id = current_said_id

        # Add final paragraph
        if current_paragraph_parts:
            paragraph_text = " ".join(current_paragraph_parts)
            wrapped_lines = textwrap.wrap(
                paragraph_text, width=79, break_long_words=False, break_on_hyphens=False
            )
            paragraphs.append("\n".join(wrapped_lines))

        return "\n\n".join(paragraphs)

    def _remove_accents(self, text: str) -> str:
        """
        Remove Greek accents and diacritics from text.

        Args:
            text: Text that may contain Greek accents

        Returns:
            Text with accents removed
        """
        # Normalize to NFD (decomposed form) to separate base letters from accents
        nfd = unicodedata.normalize('NFD', text)
        # Filter out combining diacritical marks (category Mn)
        without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
        return without_accents

    def _format_book_header(self, book_num: str) -> str:
        """
        Format book header in standard text critical edition format.

        Args:
            book_num: Book number as string (e.g., "1", "2", "10")

        Returns:
            Formatted book header (e.g., "ΠΟΛΙΤΕΊΑ Α", "ΠΟΛΙΤΕΊΑ Β")
        """
        # Greek uppercase numerals
        greek_numerals = {
            "1": "Α", "2": "Β", "3": "Γ", "4": "Δ", "5": "Ε",
            "6": "ΣΤ", "7": "Ζ", "8": "Η", "9": "Θ", "10": "Ι",
            "11": "ΙΑ", "12": "ΙΒ", "13": "ΙΓ", "14": "ΙΔ", "15": "ΙΕ",
            "16": "ΙΣΤ", "17": "ΙΖ", "18": "ΙΗ", "19": "ΙΘ", "20": "Κ"
        }

        numeral = greek_numerals.get(book_num, book_num)
        # Use uppercase title without accents with book number
        title_upper = self._remove_accents(self.title.upper()) if self.title else ""
        return f"{title_upper} {numeral}"

    def _format_stephanus(self, stephanus_list: List[str]) -> str:
        """
        Format Stephanus pagination markers according to convention.

        Rules:
        - First section of a page (e.g., "2", "2a") -> "[2]"
        - Subsequent sections (e.g., "2b", "2c") -> "[b]", "[c]"

        Args:
            stephanus_list: List of Stephanus markers (e.g., ["2", "2a"] or ["2b"])

        Returns:
            Formatted Stephanus marker string
        """
        if not stephanus_list:
            return ""

        # Check if this is a first section (has both page number and page+a)
        # Example: ["2", "2a"] or ["3", "3a"]
        if len(stephanus_list) >= 2:
            # This is the first section - just show the page number
            page_num = stephanus_list[0]
            return f"[{page_num}]"

        # Single marker - extract just the letter part for subsequent sections
        marker = stephanus_list[0]

        # Check if it ends with a letter (2b, 2c, etc.)
        if len(marker) > 1 and marker[-1].isalpha():
            letter = marker[-1]
            return f"[{letter}]"

        # Shouldn't reach here, but return as-is if we do
        return f"[{marker}]"

    def _format_no_punctuation_no_labels(self) -> str:
        """
        Format as Style D: No punctuation, no labels, no paragraphs.

        Preserves:
        - Word boundaries (spaces)
        - Stephanus pagination markers
        - Text wrapped at 79 characters
        Removes:
        - All punctuation
        - Speaker labels
        - Paragraph breaks (continuous text with single spaces)
        - M-dashes (replaced with spaces)
        """
        if not self.dialogue_data:
            return ""

        # Normalize m-dashes for Style D
        normalized_data = self._normalize_dashes(self.dialogue_data)

        # Collect all text with Stephanus markers but without labels
        # Track last page number to format markers correctly
        text_parts = []
        last_page_num = None

        for entry in normalized_data:
            # Add Stephanus markers (only first one for Style D)
            if entry["stephanus"]:
                stephanus_marker = self._format_stephanus_with_context(
                    entry["stephanus"], last_page_num
                )
                if stephanus_marker:
                    text_parts.append(stephanus_marker)
                    # Update last page number
                    last_page_num = self._extract_page_number(entry["stephanus"])

            # Remove all punctuation but keep spaces
            text = entry["text"]
            punctuation_pattern = r"[.,;·?!()[\]\"\"''ʼ—\-]"
            text_no_punct = re.sub(punctuation_pattern, "", text)
            text_parts.append(text_no_punct)

        # Join all text with single spaces (no paragraph breaks)
        continuous_text = " ".join(text_parts)

        # Wrap at 79 characters
        wrapped_lines = textwrap.wrap(
            continuous_text, width=79, break_long_words=False, break_on_hyphens=False
        )

        return "\n".join(wrapped_lines)

    def _format_scriptio_continua(self) -> str:
        """
        Format as Style E: Ancient Greek scriptio continua.

        Characteristics:
        - ALL UPPERCASE
        - No accents (diacritics removed)
        - No word boundaries (no spaces)
        - No punctuation
        - No speaker labels
        - No Stephanus markers
        - M-dashes removed (replaced with spaces before removal of all spaces)
        - Continuous text as written in antiquity
        - Wrapped at 79 characters for readability
        """
        if not self.dialogue_data:
            return ""

        # Normalize m-dashes for Style E
        normalized_data = self._normalize_dashes(self.dialogue_data)

        # Extract just the text from all entries
        all_text = " ".join(entry["text"] for entry in normalized_data)

        # Convert to uppercase
        text_upper = all_text.upper()

        # Remove all punctuation
        # Greek punctuation marks: . , ; · ? ! ( ) [ ] " " ' ' ʼ
        # Also remove Latin punctuation and apostrophes
        punctuation_pattern = r"[.,;·?!()[\]\"\"''ʼ—\-]"
        text_no_punct = re.sub(punctuation_pattern, "", text_upper)

        # Remove all spaces (scriptio continua = continuous writing)
        text_continuous = text_no_punct.replace(" ", "")

        # Remove Greek accents/diacritics
        # Greek combining diacritical marks (Unicode ranges)
        text_no_accents = unicodedata.normalize('NFD', text_continuous)
        text_no_accents = ''.join(char for char in text_no_accents
                                   if unicodedata.category(char) != 'Mn')

        # Wrap at 79 characters for readability
        # For scriptio continua (no spaces), we need break_long_words=True
        wrapped_lines = textwrap.wrap(
            text_no_accents, width=79, break_long_words=True, break_on_hyphens=False
        )

        return "\n".join(wrapped_lines)

    def _format_minimal_punctuation(self) -> str:
        """
        Format as Style B: Minimal punctuation.

        Preserves:
        - Periods, question marks (;), and colons (·)
        - Speaker labels (only when speaker changes)
        - Stephanus markers (simplified format)
        - Text wrapped at 79 characters
        - Paragraphs separated by empty lines (one paragraph per <said> element)
        Removes:
        - Commas
        - M-dashes (replaced with spaces)
        """
        if not self.dialogue_data:
            return ""

        # Normalize m-dashes for Style B and beyond
        normalized_data = self._normalize_dashes(self.dialogue_data)

        # Build paragraphs (one per <said> element)
        paragraphs = []
        current_paragraph_parts = []
        last_page_num = None
        last_speaker = None
        last_said_id = None

        for entry in normalized_data:
            current_speaker = entry["speaker"]
            current_said_id = entry.get("said_id")
            is_paragraph_start = entry.get("is_paragraph_start", False)

            # Start new paragraph if:
            # 1. We're in a different <said> element, OR
            # 2. This entry is marked as a paragraph start (from <milestone unit="para"/>)
            if (current_said_id != last_said_id and last_said_id is not None) or is_paragraph_start:
                # Finish current paragraph
                if current_paragraph_parts:
                    paragraph_text = " ".join(current_paragraph_parts)
                    wrapped_lines = textwrap.wrap(
                        paragraph_text, width=79, break_long_words=False, break_on_hyphens=False
                    )
                    paragraphs.append("\n".join(wrapped_lines))
                    current_paragraph_parts = []

            line_parts = []

            # Add Stephanus markers with simplified formatting
            if entry["stephanus"]:
                stephanus_marker = self._format_stephanus_with_context(
                    entry["stephanus"], last_page_num
                )
                if stephanus_marker:
                    line_parts.append(stephanus_marker)
                    last_page_num = self._extract_page_number(entry["stephanus"])

            # Add speaker label only if speaker changed
            if entry["label"] and current_speaker != last_speaker:
                line_parts.append(entry["label"])

            # Remove only commas
            text = entry["text"]
            text = text.replace(",", "")

            line_parts.append(text)

            current_paragraph_parts.append(" ".join(line_parts))
            last_speaker = current_speaker
            last_said_id = current_said_id

        # Add final paragraph
        if current_paragraph_parts:
            paragraph_text = " ".join(current_paragraph_parts)
            wrapped_lines = textwrap.wrap(
                paragraph_text, width=79, break_long_words=False, break_on_hyphens=False
            )
            paragraphs.append("\n".join(wrapped_lines))

        return "\n\n".join(paragraphs)

    def _format_no_punctuation(self) -> str:
        """
        Format as Style C: No punctuation.

        Preserves:
        - Speaker labels (only when speaker changes)
        - Stephanus markers (simplified format)
        - Word boundaries (spaces)
        - Text wrapped at 79 characters
        - Paragraphs separated by empty lines (one paragraph per <said> element)
        Removes:
        - All punctuation
        - M-dashes (replaced with spaces)
        """
        if not self.dialogue_data:
            return ""

        # Normalize m-dashes for Style C
        normalized_data = self._normalize_dashes(self.dialogue_data)

        # Build paragraphs (one per <said> element)
        paragraphs = []
        current_paragraph_parts = []
        last_page_num = None
        last_speaker = None
        last_said_id = None

        for entry in normalized_data:
            current_speaker = entry["speaker"]
            current_said_id = entry.get("said_id")
            is_paragraph_start = entry.get("is_paragraph_start", False)

            # Start new paragraph if:
            # 1. We're in a different <said> element, OR
            # 2. This entry is marked as a paragraph start (from <milestone unit="para"/>)
            if (current_said_id != last_said_id and last_said_id is not None) or is_paragraph_start:
                # Finish current paragraph
                if current_paragraph_parts:
                    paragraph_text = " ".join(current_paragraph_parts)
                    wrapped_lines = textwrap.wrap(
                        paragraph_text, width=79, break_long_words=False, break_on_hyphens=False
                    )
                    paragraphs.append("\n".join(wrapped_lines))
                    current_paragraph_parts = []

            line_parts = []

            # Add Stephanus markers with simplified formatting
            if entry["stephanus"]:
                stephanus_marker = self._format_stephanus_with_context(
                    entry["stephanus"], last_page_num
                )
                if stephanus_marker:
                    line_parts.append(stephanus_marker)
                    last_page_num = self._extract_page_number(entry["stephanus"])

            # Add speaker label only if speaker changed
            if entry["label"] and current_speaker != last_speaker:
                line_parts.append(entry["label"])

            # Remove all punctuation but keep spaces
            text = entry["text"]
            punctuation_pattern = r"[.,;·?!()[\]\"\"''—\-]"
            text_no_punct = re.sub(punctuation_pattern, "", text)

            line_parts.append(text_no_punct)

            current_paragraph_parts.append(" ".join(line_parts))
            last_speaker = current_speaker
            last_said_id = current_said_id

        # Add final paragraph
        if current_paragraph_parts:
            paragraph_text = " ".join(current_paragraph_parts)
            wrapped_lines = textwrap.wrap(
                paragraph_text, width=79, break_long_words=False, break_on_hyphens=False
            )
            paragraphs.append("\n".join(wrapped_lines))

        return "\n\n".join(paragraphs)

    def _format_stephanus_layout(self) -> str:
        """
        Format as Style S: Approximation of 1578 Stephanus edition layout.

        Characteristics:
        - Narrow columns (40 characters, typical of Renaissance two-column format)
        - Stephanus section markers in left margin
        - Preserves all punctuation and text
        - No speaker labels (not in original)
        - Continuous text flow across speaker changes
        - M-dashes removed (replaced with spaces)

        Raises:
            InvalidStyleError: If used with non-Platonic works
        """
        # Validate that this is a Platonic work (tlg0059)
        if self.parser:
            author_id = self.parser.get_author_id()
            if author_id and author_id != "tlg0059":
                from pi_grapheion.exceptions import InvalidStyleError
                raise InvalidStyleError(
                    "S (Stephanus layout)",
                    "This style is only valid for Plato's works (tlg0059). "
                    "Stephanus pagination refers to the 1578 edition of Plato by Henri Estienne (Stephanus)."
                )

        if not self.dialogue_data:
            return ""

        # Normalize m-dashes for Style S
        normalized_data = self._normalize_dashes(self.dialogue_data)

        # Store normalized data temporarily for extraction
        original_data = self.dialogue_data
        self.dialogue_data = normalized_data

        # For Style S, we need to re-extract text with milestone positions
        # because the standard extractor collects all milestones at the beginning
        text_with_markers = self._extract_text_with_inline_markers()

        # Restore original data
        self.dialogue_data = original_data

        return self._format_with_margin_markers(text_with_markers)

    def _extract_text_with_inline_markers(self) -> List[Dict[str, any]]:
        """
        Re-extract text from the dialogue data, splitting at milestone markers.

        This is needed for Style G because milestones can appear mid-text.

        Returns:
            List of dicts with 'text' and 'marker' keys
        """
        if self.extractor is None:
            # Fallback: use existing dialogue data without proper splitting
            result = []
            for entry in self.dialogue_data:
                text = entry["text"]
                stephanus = entry["stephanus"]

                marker = ""
                if stephanus:
                    marker = self._format_stephanus_marker(stephanus)

                result.append({
                    "text": text,
                    "marker": marker
                })
            return result

        # Use the extractor to get properly split text
        segments = self.extractor.get_text_with_inline_milestones()

        result = []
        for segment in segments:
            text = segment["text"]
            stephanus = segment["stephanus"]

            marker = ""
            if stephanus:
                marker = self._format_stephanus_marker(stephanus)

            result.append({
                "text": text,
                "marker": marker
            })

        return result

    def _format_with_margin_markers(self, text_with_markers: List[Dict[str, any]]) -> str:
        """
        Format text with markers in the left margin.

        Text flows continuously until a marker is encountered, at which point
        a new line begins with that marker. Lines are filled to 40 characters.

        Args:
            text_with_markers: List of dicts with 'text' and 'marker' keys

        Returns:
            Formatted string with margin markers
        """
        column_width = 40
        margin_width = 6
        output_lines = []

        # Accumulate text continuously, tracking pending marker for first line
        accumulated_text = ""
        pending_marker = None  # Marker waiting to be placed on next line

        for i, item in enumerate(text_with_markers):
            text = item["text"]
            marker = item["marker"]

            # If this segment has a marker, we must break before it
            if marker:
                # Output all previously accumulated text (with pending marker if any)
                if accumulated_text and pending_marker:
                    # We have pending marker - wrap and output first line with it
                    wrapped = textwrap.wrap(
                        accumulated_text, width=column_width, break_long_words=False, break_on_hyphens=False
                    )
                    output_lines.append(f"{pending_marker:>{margin_width}} {wrapped[0]}")
                    # Output remaining lines
                    for line in wrapped[1:]:
                        output_lines.append(f"{' ' * margin_width} {line}")
                    pending_marker = None
                    accumulated_text = ""
                elif accumulated_text:
                    # No pending marker - just output accumulated text
                    wrapped = textwrap.wrap(
                        accumulated_text, width=column_width, break_long_words=False, break_on_hyphens=False
                    )
                    for line in wrapped:
                        output_lines.append(f"{' ' * margin_width} {line}")
                    accumulated_text = ""

                # Start fresh accumulation with this new marker pending
                accumulated_text = text
                pending_marker = marker
            else:
                # No marker - add to accumulation
                if accumulated_text:
                    accumulated_text += " " + text
                else:
                    accumulated_text = text

        # Handle any final accumulated text
        if pending_marker and accumulated_text:
            # Final text with pending marker - wrap it properly
            wrapped = textwrap.wrap(
                accumulated_text, width=column_width, break_long_words=False, break_on_hyphens=False
            )
            if wrapped:
                output_lines.append(f"{pending_marker:>{margin_width}} {wrapped[0]}")
                for line in wrapped[1:]:
                    output_lines.append(f"{' ' * margin_width} {line}")
        elif accumulated_text:
            # Final text without marker
            wrapped = textwrap.wrap(
                accumulated_text, width=column_width, break_long_words=False, break_on_hyphens=False
            )
            for line in wrapped:
                output_lines.append(f"{' ' * margin_width} {line}")

        return "\n".join(output_lines)

    def _format_stephanus_marker(self, stephanus_list: List[str]) -> str:
        """
        Format a single Stephanus marker for margin display.

        Args:
            stephanus_list: List of Stephanus markers (e.g., ["2", "2a"] or ["2b"] or ["4c", "4d", "4e"])

        Returns:
            Formatted marker (e.g., "[2]" or "[b]" or "[c]")
        """
        if not stephanus_list:
            return ""

        # Get the first marker in the list
        first_marker = stephanus_list[0]

        # Check if this is a TRUE page-start marker (pure number without letter)
        # Example: ["2", "2a"] where first element is "2" -> show "[2]"
        if first_marker.isdigit():
            return f"[{first_marker}]"

        # For section markers (e.g., "2b", "4c", "9c"), always show just the letter
        # This applies whether it's a single marker ["2b"] or multiple ["4c", "4d", "4e"]
        # Extract the letter from the first marker
        if len(first_marker) > 1 and first_marker[-1].isalpha():
            return f"[{first_marker[-1]}]"

        # Fallback (shouldn't normally occur)
        return f"[{first_marker}]"

    def _extract_page_number(self, stephanus_list: List[str]) -> str:
        """
        Extract the page number from a Stephanus marker list.

        Args:
            stephanus_list: List of Stephanus markers

        Returns:
            Page number as string (e.g., "58" from ["58b"])
        """
        if not stephanus_list:
            return None

        first_marker = stephanus_list[0]

        # If it's a pure number, return it
        if first_marker.isdigit():
            return first_marker

        # If it's number+letter (e.g., "58b"), extract the number
        if len(first_marker) > 1 and first_marker[-1].isalpha():
            return first_marker[:-1]

        return None

    def _format_all_stephanus_with_context(self, stephanus_list: List[str], last_page_num: str) -> List[str]:
        """
        Format ALL Stephanus markers in a list with context awareness.

        This is used for Style D where we want to show all markers in an entry.

        Args:
            stephanus_list: List of Stephanus markers for this entry
            last_page_num: The last page number that was shown (or None)

        Returns:
            List of formatted marker strings
        """
        if not stephanus_list:
            return []

        formatted_markers = []
        current_page = last_page_num

        for marker in stephanus_list:
            # Format this marker with current context
            formatted = self._format_single_marker_with_context(marker, current_page)
            if formatted:
                formatted_markers.append(formatted)
                # Update current page for next marker
                if marker.isdigit():
                    current_page = marker
                elif len(marker) > 1 and marker[-1].isalpha():
                    current_page = marker[:-1]

        return formatted_markers

    def _format_single_marker_with_context(self, marker: str, last_page_num: str) -> str:
        """
        Format a single Stephanus marker with context awareness.

        Args:
            marker: A single Stephanus marker (e.g., "61a", "61b", "62")
            last_page_num: The last page number shown

        Returns:
            Formatted marker string
        """
        # If it's a pure digit, it's a new page start
        if marker.isdigit():
            return f"[{marker}]"

        # It's number+letter (e.g., "61a")
        if len(marker) > 1 and marker[-1].isalpha():
            current_page = marker[:-1]
            letter = marker[-1]

            # If we're on the same page as last time, show only the letter
            if last_page_num and current_page == last_page_num:
                return f"[{letter}]"
            # If it's 'a' (first section), show the full page number
            elif letter == 'a':
                return f"[{current_page}]"
            # Otherwise show just the letter (subsequent section)
            else:
                return f"[{letter}]"

        # Fallback
        return f"[{marker}]"

    def _format_stephanus_with_context(self, stephanus_list: List[str], last_page_num: str) -> str:
        """
        Format Stephanus marker with awareness of previous page number.

        Args:
            stephanus_list: List of Stephanus markers for this entry
            last_page_num: The last page number that was shown (or None)

        Returns:
            Formatted marker string
        """
        if not stephanus_list:
            return ""

        # Check if this is a first section (has both page number and page+a)
        # Example: ["2", "2a"] or ["3", "3a"]
        # Key: First element must be pure number, second must be number+a
        if (len(stephanus_list) >= 2 and
            stephanus_list[0].isdigit() and
            len(stephanus_list[1]) > 1 and
            stephanus_list[1][-1] == 'a'):
            # This is the first section - just show the page number
            page_num = stephanus_list[0]
            return f"[{page_num}]"

        # Get the first marker
        first_marker = stephanus_list[0]

        # If it's a pure digit, it's a new page start
        if first_marker.isdigit():
            return f"[{first_marker}]"

        # It's number+letter (e.g., "58b", "1012b")
        if len(first_marker) > 1 and first_marker[-1].isalpha():
            current_page = first_marker[:-1]
            letter = first_marker[-1]

            # If this is the first marker (no previous context)
            if last_page_num is None:
                # If it's 'a', show just the page number (Plato convention)
                if letter == 'a':
                    return f"[{current_page}]"
                # Otherwise show the full marker (e.g., [1012b] for Plutarch)
                else:
                    return f"[{first_marker}]"
            # If we're on the same page as last time, show only the letter
            elif current_page == last_page_num:
                return f"[{letter}]"
            # If it's 'a' (first section of a new page), show the full page number
            elif letter == 'a':
                return f"[{current_page}]"
            # Otherwise show the full marker (transitioning to new page with non-'a')
            else:
                return f"[{first_marker}]"

        # Fallback
        return f"[{first_marker}]"
