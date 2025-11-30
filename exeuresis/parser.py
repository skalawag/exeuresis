"""TEI XML Parser for Perseus texts."""

from pathlib import Path
from typing import Dict, List

from lxml import etree

from exeuresis.exceptions import InvalidTEIStructureError


class TEIParser:
    """Parser for TEI XML files from the Perseus Digital Library."""

    # TEI and XML namespaces
    NS = {
        "tei": "http://www.tei-c.org/ns/1.0",
        "xml": "http://www.w3.org/XML/1998/namespace",
    }

    def __init__(self, xml_path: Path):
        """
        Initialize parser with path to TEI XML file.

        Args:
            xml_path: Path to the TEI XML file

        Raises:
            FileNotFoundError: If the XML file doesn't exist
            InvalidTEIStructureError: If the XML is missing required TEI elements
        """
        if not xml_path.exists():
            raise FileNotFoundError(f"XML file not found: {xml_path}")

        self.xml_path = xml_path
        self.tree = etree.parse(str(xml_path))
        self.root = self.tree.getroot()

        # Validate basic TEI structure
        self._validate_structure()

    def get_speakers(self) -> List[str]:
        """
        Extract speaker names from the TEI header.

        Returns:
            List of speaker names found in particDesc/person elements
        """
        speakers = []
        # Find all persName elements in particDesc
        person_names = self.root.findall(
            ".//tei:particDesc/tei:person/tei:persName", self.NS
        )

        for person in person_names:
            if person.text:
                speakers.append(person.text)

        return speakers

    def get_title(self) -> str:
        """
        Extract the Greek title from the TEI header.

        Returns:
            Greek title string, or empty string if not found
        """
        # Find title element with xml:lang="grc"
        # Note: Use {http://...} notation for xml:lang attribute
        title_elements = self.root.findall(".//tei:titleStmt/tei:title", self.NS)
        for title_element in title_elements:
            lang = title_element.get("{http://www.w3.org/XML/1998/namespace}lang")
            if lang == "grc" and title_element.text:
                return title_element.text.strip()

        return ""

    def get_author_id(self) -> str:
        """
        Extract the author TLG ID from the file path.

        Returns:
            Author TLG ID (e.g., "tlg0059" for Plato) or empty string if not found
        """
        # File path format: .../tlg####/tlg###/tlg####.tlg###.perseus-grc#.xml
        # Extract the first tlg#### from the path
        path_parts = self.xml_path.parts
        for part in path_parts:
            if part.startswith("tlg") and len(part) == 7 and part[3:].isdigit():
                return part
        return ""

    def get_book_divisions(self) -> List[str]:
        """
        Extract book divisions from multi-book works.

        Returns:
            List of book numbers (e.g., ['1', '2', '3']) or empty list if no books
        """
        books = []
        # Find all div elements with type="textpart" and subtype="book"
        book_elements = self.root.findall(
            ".//tei:text/tei:body//tei:div[@type='textpart'][@subtype='book']", self.NS
        )

        for book in book_elements:
            book_num = book.get("n", "")
            if book_num:
                books.append(book_num)

        return books

    def get_divisions(self) -> List[Dict[str, str]]:
        """
        Extract text divisions (sections) from the body.

        Returns:
            List of dictionaries containing division metadata
            Each dict has keys: 'n', 'type', 'subtype'
        """
        divisions = []
        # Find all div elements with type="textpart"
        div_elements = self.root.findall(
            ".//tei:text/tei:body//tei:div[@type='textpart']", self.NS
        )

        for div in div_elements:
            division_info = {
                "n": div.get("n", ""),
                "type": div.get("type", ""),
                "subtype": div.get("subtype", ""),
            }
            divisions.append(division_info)

        return divisions

    def _validate_structure(self):
        """
        Validate that the XML has required TEI structure.

        Raises:
            InvalidTEIStructureError: If required elements are missing
        """
        # Check for <text> element
        text_elem = self.root.find(".//tei:text", self.NS)
        if text_elem is None:
            raise InvalidTEIStructureError(str(self.xml_path), "tei:text")

        # Check for <body> element
        body_elem = self.root.find(".//tei:text/tei:body", self.NS)
        if body_elem is None:
            raise InvalidTEIStructureError(str(self.xml_path), "tei:body")
