"""Catalog browser for Perseus Digital Library texts."""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from lxml import etree

from exeuresis.config import get_corpus_path
from exeuresis.exceptions import WorkNotFoundError

logger = logging.getLogger(__name__)


class PerseusAuthor:
    """Represents an author in the Perseus catalog."""

    def __init__(self, tlg_id: str, name_en: str, name_grc: str = ""):
        self.tlg_id = tlg_id
        self.name_en = name_en
        self.name_grc = name_grc

    def __str__(self):
        if self.name_grc:
            return f"{self.tlg_id}: {self.name_en} ({self.name_grc})"
        return f"{self.tlg_id}: {self.name_en}"


class PerseusWork:
    """Represents a work in the Perseus catalog."""

    def __init__(
        self,
        tlg_id: str,
        work_id: str,
        title_en: str,
        title_grc: str = "",
        file_path: Optional[Path] = None,
        page_range: str = "",
    ):
        self.tlg_id = tlg_id
        self.work_id = work_id
        self.title_en = title_en
        self.title_grc = title_grc
        self.file_path = file_path
        self.page_range = page_range

    def __str__(self):
        if self.title_grc:
            result = f"  {self.work_id}: {self.title_en} ({self.title_grc})"
        else:
            result = f"  {self.work_id}: {self.title_en}"
        if self.page_range:
            result += f" [{self.page_range}]"
        if self.file_path:
            result += f"\n    File: {self.file_path}"
        return result


class PerseusCatalog:
    """Catalog browser for Perseus Digital Library texts."""

    # CTS namespace
    NS = {"ti": "http://chs.harvard.edu/xmlns/cts"}

    def __init__(self, data_dir: Path = None):
        """
        Initialize catalog with path to canonical-greekLit/data directory.

        Args:
            data_dir: Path to the data directory (default: from config or canonical-greekLit/data)
        """
        if data_dir is None:
            self.data_dir = get_corpus_path()
        else:
            self.data_dir = Path(data_dir)

        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

    def list_authors(self) -> List[PerseusAuthor]:
        """
        List all authors in the catalog.

        Returns:
            List of PerseusAuthor objects, sorted by TLG ID
        """
        authors = []

        # Iterate through tlg directories
        for author_dir in sorted(self.data_dir.glob("tlg*")):
            if not author_dir.is_dir():
                continue

            # Read __cts__.xml for author metadata
            cts_file = author_dir / "__cts__.xml"
            if not cts_file.exists():
                continue

            try:
                tree = etree.parse(str(cts_file))
                root = tree.getroot()

                # Extract author name (English and Greek if available)
                # Find all groupname elements and filter by xml:lang
                groupnames = root.findall(".//ti:groupname", self.NS)

                name_en = ""
                name_grc = ""

                for elem in groupnames:
                    lang = elem.get("{http://www.w3.org/XML/1998/namespace}lang")
                    if lang in ("en", "eng", "lat") and elem.text and not name_en:
                        name_en = elem.text.strip()
                    elif lang == "grc" and elem.text:
                        name_grc = elem.text.strip()
                    elif not lang and elem.text and not name_en:
                        # Fallback: use element without lang attribute
                        name_en = elem.text.strip()

                if name_en:
                    authors.append(
                        PerseusAuthor(author_dir.name, name_en, name_grc)
                    )
            except Exception as e:
                # Skip authors with malformed metadata
                logger.warning(
                    f"Skipping author {author_dir.name}: malformed metadata - {e}"
                )
                logger.debug(f"Failed to parse {cts_file}", exc_info=True)
                continue

        return authors

    def list_works(self, tlg_id: str) -> List[PerseusWork]:
        """
        List all works for a specific author.

        Args:
            tlg_id: Author TLG ID (e.g., "tlg0059" for Plato)

        Returns:
            List of PerseusWork objects
        """
        works = []
        author_dir = self.data_dir / tlg_id

        if not author_dir.exists():
            return works

        # Iterate through work directories
        for work_dir in sorted(author_dir.glob("tlg*")):
            if not work_dir.is_dir():
                continue

            # Read __cts__.xml for work metadata
            cts_file = work_dir / "__cts__.xml"
            if not cts_file.exists():
                continue

            try:
                tree = etree.parse(str(cts_file))
                root = tree.getroot()

                # Extract work title (English and Greek if available)
                # Find all title and label elements
                titles = root.findall(".//ti:title", self.NS)
                labels = root.findall(".//ti:edition/ti:label", self.NS)

                title_en = ""
                title_grc = ""

                # Look for English or Latin title
                for elem in titles:
                    lang = elem.get("{http://www.w3.org/XML/1998/namespace}lang")
                    if lang in ("eng", "lat") and elem.text:
                        title_en = elem.text.strip()
                        break

                # Look for Greek title in edition label
                for elem in labels:
                    lang = elem.get("{http://www.w3.org/XML/1998/namespace}lang")
                    if lang == "grc" and elem.text:
                        title_grc = elem.text.strip()
                        break

                if title_en:
                    # Find the Greek edition file
                    greek_files = list(work_dir.glob("*.perseus-grc*.xml"))
                    file_path = greek_files[0] if greek_files else None

                    # Extract page range if we have a file
                    page_range = ""
                    if file_path:
                        page_range = self._extract_page_range(file_path)

                    works.append(
                        PerseusWork(
                            tlg_id, work_dir.name, title_en, title_grc, file_path, page_range
                        )
                    )
            except Exception as e:
                # Skip works with malformed metadata
                logger.warning(
                    f"Skipping work {tlg_id}/{work_dir.name}: malformed metadata - {e}"
                )
                logger.debug(f"Failed to parse {cts_file}", exc_info=True)
                continue

        return works

    def search_works(self, query: str) -> List[tuple[PerseusAuthor, PerseusWork]]:
        """
        Search for works by title or author name.

        Args:
            query: Search string (case-insensitive)

        Returns:
            List of (author, work) tuples matching the query
        """
        results = []
        query_lower = query.lower()

        for author in self.list_authors():
            # Check if author name matches
            author_matches = (
                query_lower in author.name_en.lower()
                or query_lower in author.name_grc.lower()
            )

            # Get author's works
            works = self.list_works(author.tlg_id)

            for work in works:
                # Check if work title matches
                work_matches = (
                    query_lower in work.title_en.lower()
                    or query_lower in work.title_grc.lower()
                )

                # Add to results if either author or work matches
                if author_matches or work_matches:
                    results.append((author, work))

        return results

    def get_author_info(self, tlg_id: str) -> Optional[PerseusAuthor]:
        """
        Get information about a specific author.

        Args:
            tlg_id: Author TLG ID (e.g., "tlg0059")

        Returns:
            PerseusAuthor object or None if not found
        """
        authors = self.list_authors()
        for author in authors:
            if author.tlg_id == tlg_id:
                return author
        return None

    def resolve_author_name(self, name: str) -> Optional[str]:
        """
        Resolve an author name to their TLG ID.

        Args:
            name: Author name (English or Greek, case-insensitive) or TLG ID

        Returns:
            Author TLG ID (e.g., "tlg0059") or None if not found or ambiguous

        Examples:
            "Plato" -> "tlg0059"
            "plato" -> "tlg0059"
            "Πλάτων" -> "tlg0059"
            "tlg0059" -> "tlg0059" (pass-through)
        """
        # If it's already a TLG ID, return it as-is
        if name.startswith("tlg"):
            return name if self.get_author_info(name) else None

        # Search for matching authors
        name_lower = name.lower()
        matches = []

        for author in self.list_authors():
            if (name_lower == author.name_en.lower() or
                name_lower == author.name_grc.lower()):
                matches.append(author.tlg_id)

        # Return match if exactly one found, None if ambiguous or not found
        return matches[0] if len(matches) == 1 else None

    def _extract_page_range(self, xml_file: Path) -> str:
        """
        Extract the Stephanus page range or section range from a TEI XML file.

        Args:
            xml_file: Path to the TEI XML file

        Returns:
            Page range string (e.g., "2-16", "327-621", "1-52") or empty string if none found
        """
        try:
            # TEI namespace
            NS = {"tei": "http://www.tei-c.org/ns/1.0"}

            tree = etree.parse(str(xml_file))
            root = tree.getroot()

            # Find all milestone elements with unit="section" or unit="stephpage"
            # Plato uses unit="section", Plutarch uses unit="stephpage"
            milestones = root.xpath(
                "//tei:milestone[@unit='section' or @unit='stephpage']/@n",
                namespaces=NS
            )

            # Also find section divs (Isocrates and other authors use these)
            section_divs = root.xpath(
                "//tei:div[@type='textpart' and @subtype='section']/@n",
                namespaces=NS
            )

            # Combine both types
            all_markers = milestones + section_divs

            if not all_markers:
                return ""

            # Extract page numbers from Stephanus markers (e.g., "327a" -> 327, "1012b" -> 1012)
            # or section numbers (e.g., "1", "2", "52")
            pages = set()
            for marker in all_markers:
                # Skip special markers like "chunk"
                if not any(c.isdigit() for c in marker):
                    continue

                # Extract numeric part (page number or section number)
                page_num = ""
                for char in marker:
                    if char.isdigit():
                        page_num += char
                    else:
                        break
                if page_num:
                    pages.add(int(page_num))

            if not pages:
                return ""

            # Return range as "min-max" or just "min" if only one page
            sorted_pages = sorted(pages)
            if len(sorted_pages) == 1:
                return str(sorted_pages[0])
            else:
                return f"{sorted_pages[0]}-{sorted_pages[-1]}"

        except Exception as e:
            logger.debug(f"Could not extract page range from {xml_file}: {e}")
            return ""

    def resolve_work_id(self, work_id: str) -> Path:
        """
        Resolve a work ID to its file path.

        Args:
            work_id: Work ID in format "tlg####.tlg###" (e.g., "tlg0059.tlg001")

        Returns:
            Path to the Greek edition file

        Raises:
            WorkNotFoundError: If the work ID is invalid or not found
        """
        # Validate format
        parts = work_id.split(".")
        if len(parts) != 2:
            raise WorkNotFoundError(
                work_id,
                "Work ID must be in format 'tlg####.tlg###' (e.g., tlg0059.tlg001)"
            )

        author_id, work_num = parts

        # Validate IDs start with "tlg"
        if not author_id.startswith("tlg") or not work_num.startswith("tlg"):
            raise WorkNotFoundError(
                work_id,
                "Both author and work must start with 'tlg'"
            )

        # Check if author exists
        author = self.get_author_info(author_id)
        if not author:
            raise WorkNotFoundError(
                work_id,
                f"Author '{author_id}' not found. Use 'list-authors' to see available authors."
            )

        # Get works for this author
        works = self.list_works(author_id)

        # Find matching work
        for work in works:
            if work.work_id == work_num:
                if work.file_path:
                    return work.file_path
                else:
                    raise WorkNotFoundError(
                        work_id,
                        f"Work found but no Greek edition file available"
                    )

        # Work not found - provide helpful suggestion
        raise WorkNotFoundError(
            work_id,
            f"Work '{work_num}' not found for author {author.name_en}.\n"
            f"Use 'list-works {author_id}' to see available works."
        )
