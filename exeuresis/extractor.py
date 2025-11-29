"""Text extraction from parsed TEI XML."""

from typing import List, Dict
from lxml import etree

from exeuresis.exceptions import EmptyExtractionError


class TextExtractor:
    """Extracts text content from parsed TEI XML documents."""

    # TEI namespace
    NS = {"tei": "http://www.tei-c.org/ns/1.0"}

    def __init__(self, parser):
        """
        Initialize extractor with a TEIParser instance.

        Args:
            parser: An initialized TEIParser instance
        """
        self.parser = parser
        self.root = parser.root
        self.is_dialogue = self._detect_text_type()

    def _detect_text_type(self) -> bool:
        """
        Detect whether this is a dialogue or non-dialogue text.

        Returns:
            True if text contains <said> elements (dialogue), False otherwise
        """
        said_elements = self.root.findall(".//tei:said", self.NS)
        return len(said_elements) > 0

    def get_dialogue_text(self) -> List[Dict[str, any]]:
        """
        Extract all text from the document (dialogue or non-dialogue).

        Text is split at Stephanus milestone boundaries so that each entry
        has its milestone at the beginning, not collected at the start.

        Returns:
            List of dictionaries, each containing:
                - speaker: Full speaker name (e.g., "Εὐθύφρων") or empty string
                - label: Speaker abbreviation (e.g., "ΕΥΘ.") or empty string
                - text: The text content (cleaned)
                - stephanus: List of Stephanus pagination markers

        Raises:
            EmptyExtractionError: If no text content is extracted
        """
        if self.is_dialogue:
            result = self._extract_dialogue_split_at_milestones()
        else:
            result = self._extract_non_dialogue_split_at_milestones()

        # Check if we extracted any actual text
        if not result:
            raise EmptyExtractionError(
                str(self.parser.xml_path),
                "No text elements found in document"
            )

        # Check if all entries are empty
        has_text = any(entry.get("text", "").strip() for entry in result)
        if not has_text:
            raise EmptyExtractionError(
                str(self.parser.xml_path),
                "All extracted entries are empty"
            )

        return result

    def _extract_dialogue_split_at_milestones(self) -> List[Dict[str, any]]:
        """
        Extract dialogue text, splitting at milestone boundaries.

        Each <said> element is split at Stephanus milestone markers so that
        each segment has its milestone at the beginning where it occurs.

        Returns:
            List of dialogue entries with speaker, label, text, stephanus, said_id, and book
        """
        dialogue = []

        # Find all <said> elements
        said_elements = self.root.findall(".//tei:said", self.NS)

        for said_index, said in enumerate(said_elements):
            # Extract speaker and label (same for all segments from this <said>)
            speaker_attr = said.get("who", "")
            speaker = speaker_attr.lstrip("#")

            label_element = said.find("tei:label", self.NS)
            label = label_element.text if label_element is not None else ""

            # Find which book this <said> element is in
            book_num = self._find_book_number(said)

            # Split this <said> element at milestone boundaries
            segments = self._split_at_milestones(said)

            # Add speaker, label, said_id, book, and paragraph flag to each segment
            for segment in segments:
                dialogue.append({
                    "speaker": speaker,
                    "label": label,
                    "text": segment["text"],
                    "stephanus": segment["stephanus"],
                    "said_id": said_index,  # Track which <said> this came from
                    "is_paragraph_start": segment.get("is_paragraph_start", False),
                    "book": book_num,  # Track which book this came from
                })

        return dialogue

    def _extract_non_dialogue_split_at_milestones(self) -> List[Dict[str, any]]:
        """
        Extract non-dialogue text, splitting at milestone boundaries.

        Each <p> element is split at Stephanus milestone markers so that
        each segment has its milestone at the beginning where it occurs.

        Returns:
            List of text entries with empty speaker/label, text, stephanus, said_id, and book
        """
        entries = []

        # Find all <p> elements within the text body
        p_elements = self.root.findall(".//tei:text//tei:p", self.NS)

        for p_index, p in enumerate(p_elements):
            # Find which book this <p> element is in
            book_num = self._find_book_number(p)

            # Find which section this <p> element is in
            section_num = self._find_section_number(p)

            # Split this <p> element at milestone boundaries
            segments = self._split_at_milestones(p)

            # Add empty speaker/label, p_index, book, and paragraph flag to each segment
            for segment in segments:
                # If this paragraph is in a section div, add section number to stephanus markers
                stephanus = segment["stephanus"].copy() if segment["stephanus"] else []
                if section_num and not stephanus:
                    # Only add section number if there are no milestone markers
                    stephanus = [section_num]

                entries.append({
                    "speaker": "",
                    "label": "",
                    "text": segment["text"],
                    "stephanus": stephanus,
                    "said_id": p_index,  # Track which <p> this came from
                    "is_paragraph_start": segment.get("is_paragraph_start", False),
                    "book": book_num,  # Track which book this came from
                })

        return entries

    def _extract_dialogue(self) -> List[Dict[str, any]]:
        """
        Extract dialogue text from <said> elements.

        Returns:
            List of dialogue entries
        """
        dialogue = []

        # Find all <said> elements
        said_elements = self.root.findall(".//tei:said", self.NS)

        for said in said_elements:
            entry = self._extract_said_element(said)
            dialogue.append(entry)

        return dialogue

    def _extract_non_dialogue(self) -> List[Dict[str, any]]:
        """
        Extract non-dialogue text from <p> elements.

        Returns:
            List of text entries (one per paragraph)
        """
        entries = []

        # Find all <p> elements within the text body
        p_elements = self.root.findall(".//tei:text//tei:p", self.NS)

        for p in p_elements:
            # Extract Stephanus markers
            stephanus = self._extract_stephanus_markers(p)

            # Extract text content
            text = self._extract_text_content(p)

            # Skip empty paragraphs
            if text:
                entries.append({
                    "speaker": "",
                    "label": "",
                    "text": text,
                    "stephanus": stephanus,
                })

        return entries

    def _extract_said_element(self, said_element) -> Dict[str, any]:
        """
        Extract data from a single <said> element.

        Args:
            said_element: An lxml Element representing a <said> tag

        Returns:
            Dictionary with speaker, label, text, and stephanus data
        """
        # Extract speaker from @who attribute (remove leading #)
        speaker_attr = said_element.get("who", "")
        speaker = speaker_attr.lstrip("#")

        # Extract label
        label_element = said_element.find("tei:label", self.NS)
        label = label_element.text if label_element is not None else ""

        # Extract Stephanus markers
        stephanus = self._extract_stephanus_markers(said_element)

        # Extract text content (excluding label and milestone elements)
        text = self._extract_text_content(said_element)

        return {
            "speaker": speaker,
            "label": label,
            "text": text,
            "stephanus": stephanus,
        }

    def _extract_stephanus_markers(self, element) -> List[str]:
        """
        Extract Stephanus pagination markers from milestone elements.

        Supports both Plato's section markers (unit="section") and
        Plutarch's Stephanus page markers (unit="stephpage").

        Args:
            element: An lxml Element to search within

        Returns:
            List of Stephanus marker values (e.g., ["2", "2a"])
        """
        markers = []
        # Extract section milestones (Plato texts) and stephpage milestones (Plutarch texts)
        # Note: Some section milestones don't have resp="Stephanus" but are still valid
        section_milestones = element.findall(".//tei:milestone[@unit='section']", self.NS)
        stephpage_milestones = element.findall(".//tei:milestone[@unit='stephpage']", self.NS)

        # Combine both types of milestones
        all_milestones = section_milestones + stephpage_milestones

        for milestone in all_milestones:
            n_value = milestone.get("n")
            if n_value:
                markers.append(n_value)

        return markers

    def _extract_text_content(self, element) -> str:
        """
        Extract text content from an element, excluding label and milestone tags.

        Args:
            element: An lxml Element to extract text from

        Returns:
            Cleaned text content with whitespace normalized
        """
        # Collect text from all parts except label and milestone elements
        text_parts = []

        # Get the element's direct text
        if element.text:
            text_parts.append(element.text)

        # Iterate through all children
        for child in element:
            # Skip non-element nodes (e.g., comments, processing instructions)
            if not isinstance(child.tag, str):
                if child.tail:
                    text_parts.append(child.tail)
                continue

            # Skip label and milestone elements
            if child.tag in [
                f"{{{self.NS['tei']}}}label",
                f"{{{self.NS['tei']}}}milestone",
            ]:
                # But include their tail text (text after the tag)
                if child.tail:
                    text_parts.append(child.tail)
            else:
                # For other elements, get all text recursively
                child_text = "".join(child.itertext())
                if child_text:
                    text_parts.append(child_text)
                # Also add tail text
                if child.tail:
                    text_parts.append(child.tail)

        # Join and normalize whitespace
        full_text = " ".join(text_parts)
        normalized_text = " ".join(full_text.split())

        # Remove stray gamma at end (OCR artifact in Perseus texts)
        # Pattern: gamma at end of text, often after punctuation
        if normalized_text.endswith('γ'):
            normalized_text = normalized_text[:-1].rstrip()

        return normalized_text.strip()

    def get_text_with_inline_milestones(self) -> List[Dict[str, any]]:
        """
        Extract text, splitting at milestone markers for proper positioning.

        This method splits elements at milestone boundaries so that
        each text segment has its milestone at the beginning, not collected
        at the start of the entire element.

        Returns:
            List of dictionaries with 'text' and 'stephanus' keys
        """
        result = []

        if self.is_dialogue:
            # Find all <said> elements
            elements = self.root.findall(".//tei:said", self.NS)
        else:
            # Find all <p> elements
            elements = self.root.findall(".//tei:text//tei:p", self.NS)

        for element in elements:
            # Split this element at milestone boundaries
            segments = self._split_at_milestones(element)
            result.extend(segments)

        return result

    def _find_book_number(self, element) -> str:
        """
        Find which book number an element belongs to by traversing up the tree.

        Args:
            element: An lxml Element (either <said> or <p>)

        Returns:
            Book number as string (e.g., "1", "2"), or empty string if not in a book
        """
        # Traverse up the tree to find a parent div with subtype="book"
        current = element
        while current is not None:
            # Check if this is a book div
            if (current.tag == f"{{{self.NS['tei']}}}div" and
                current.get("type") == "textpart" and
                current.get("subtype") == "book"):
                book_num = current.get("n", "")
                return book_num
            # Move to parent
            current = current.getparent()

        return ""

    def _find_section_number(self, element) -> str:
        """
        Find which section number an element belongs to by traversing up the tree.

        Args:
            element: An lxml Element (either <said> or <p>)

        Returns:
            Section number as string (e.g., "1", "2"), or empty string if not in a section
        """
        # Traverse up the tree to find a parent div with subtype="section"
        current = element
        while current is not None:
            # Check if this is a section div
            if (current.tag == f"{{{self.NS['tei']}}}div" and
                current.get("type") == "textpart" and
                current.get("subtype") == "section"):
                section_num = current.get("n", "")
                return section_num
            # Move to parent
            current = current.getparent()

        return ""

    def _split_at_milestones(self, element) -> List[Dict[str, any]]:
        """
        Split an element's text at milestone markers.

        Args:
            element: An lxml Element (either <said> or <p>)

        Returns:
            List of dicts, each with 'text', 'stephanus', and 'is_paragraph_start' keys
        """
        segments = []
        current_text_parts = []
        pending_markers = []  # Markers waiting to be attached to next segment
        is_paragraph_start = False

        # Get initial text before any children
        if element.text:
            current_text_parts.append(element.text)

        # Process all children
        for child in element:
            # Skip non-element nodes (e.g., comments, processing instructions)
            if not isinstance(child.tag, str):
                if child.tail:
                    current_text_parts.append(child.tail)
                continue

            if child.tag == f"{{{self.NS['tei']}}}milestone":
                # Check for paragraph milestone
                if child.get("ed") == "P" and child.get("unit") == "para":
                    # Save segment if we have accumulated text
                    if current_text_parts:
                        text = " ".join(current_text_parts)
                        text = " ".join(text.split()).strip()
                        # Remove stray gamma at end (OCR artifact)
                        if text.endswith('γ'):
                            text = text[:-1].rstrip()
                        if text:
                            segments.append({
                                "text": text,
                                "stephanus": pending_markers.copy(),  # Attach pending markers
                                "is_paragraph_start": is_paragraph_start
                            })
                            pending_markers = []  # Clear after attaching
                            is_paragraph_start = False
                        current_text_parts = []
                    # Mark that next segment starts a paragraph
                    is_paragraph_start = True

                # Check if this is a Stephanus section milestone (Plato) or stephpage (Plutarch)
                # Note: Some section milestones don't have resp="Stephanus" but are still valid
                elif child.get("unit") in ("section", "stephpage"):
                    # FIRST: Save current segment if it has text (with OLD pending markers)
                    if current_text_parts:
                        text = " ".join(current_text_parts)
                        text = " ".join(text.split()).strip()
                        # Remove stray gamma at end (OCR artifact)
                        if text.endswith('γ'):
                            text = text[:-1].rstrip()
                        if text:
                            segments.append({
                                "text": text,
                                "stephanus": pending_markers.copy(),  # Attach OLD pending markers
                                "is_paragraph_start": is_paragraph_start
                            })
                            is_paragraph_start = False
                        current_text_parts = []

                    # THEN: Clear pending markers and add THIS milestone as the NEW pending marker
                    pending_markers = []
                    n_value = child.get("n")
                    if n_value:
                        pending_markers.append(n_value)

                # Add tail text after the milestone
                if child.tail:
                    current_text_parts.append(child.tail)

            elif child.tag == f"{{{self.NS['tei']}}}label":
                # Skip label text but include tail
                if child.tail:
                    current_text_parts.append(child.tail)

            else:
                # For other elements, get all text
                child_text = "".join(child.itertext())
                if child_text:
                    current_text_parts.append(child_text)
                if child.tail:
                    current_text_parts.append(child.tail)

        # Add final segment
        if current_text_parts:
            text = " ".join(current_text_parts)
            text = " ".join(text.split()).strip()
            # Remove stray gamma at end (OCR artifact)
            if text.endswith('γ'):
                text = text[:-1].rstrip()
            if text:
                segments.append({
                    "text": text,
                    "stephanus": pending_markers.copy(),  # Attach any remaining pending markers
                    "is_paragraph_start": is_paragraph_start
                })

        return segments
