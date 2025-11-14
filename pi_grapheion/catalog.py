"""Catalog browser for Perseus Digital Library texts."""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from lxml import etree

from pi_grapheion.exceptions import WorkNotFoundError

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
    ):
        self.tlg_id = tlg_id
        self.work_id = work_id
        self.title_en = title_en
        self.title_grc = title_grc
        self.file_path = file_path

    def __str__(self):
        if self.title_grc:
            result = f"  {self.work_id}: {self.title_en} ({self.title_grc})"
        else:
            result = f"  {self.work_id}: {self.title_en}"
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
            data_dir: Path to the data directory (default: canonical-greekLit/data)
        """
        if data_dir is None:
            # Default to canonical-greekLit/data relative to project root
            self.data_dir = Path(__file__).parent.parent / "canonical-greekLit" / "data"
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

                    works.append(
                        PerseusWork(
                            tlg_id, work_dir.name, title_en, title_grc, file_path
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
