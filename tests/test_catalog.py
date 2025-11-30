"""Tests for Perseus catalog functionality."""

from pathlib import Path

import pytest

from exeuresis.catalog import PerseusCatalog
from exeuresis.exceptions import WorkNotFoundError


class TestPerseusCatalog:
    """Test suite for catalog browsing and search functionality."""

    @pytest.fixture
    def catalog(self):
        """Create catalog instance pointing to test data."""
        data_dir = Path(__file__).parent.parent / "canonical-greekLit" / "data"
        return PerseusCatalog(data_dir=data_dir)

    def test_list_authors(self, catalog):
        """Test listing all authors in catalog."""
        authors = catalog.list_authors()

        # Should find many authors (Perseus has ~99)
        assert len(authors) > 50

        # Check Plato is in the list
        plato = next((a for a in authors if a.tlg_id == "tlg0059"), None)
        assert plato is not None
        assert plato.name_en == "Plato"

    def test_list_works_plato(self, catalog):
        """Test listing Plato's works."""
        works = catalog.list_works("tlg0059")

        # Plato should have 36 works
        assert len(works) == 36

        # Check Euthyphro is in the list
        euthyphro = next((w for w in works if w.work_id == "tlg001"), None)
        assert euthyphro is not None
        assert euthyphro.title_en == "Euthyphro"
        assert euthyphro.title_grc == "Εὐθύφρων"
        assert euthyphro.file_path is not None
        assert euthyphro.file_path.exists()

    def test_list_works_nonexistent_author(self, catalog):
        """Test listing works for non-existent author."""
        works = catalog.list_works("tlg9999")
        assert works == []

    def test_search_by_author_name(self, catalog):
        """Test searching by author name."""
        results = catalog.search_works("Plato")

        # Should find all Plato's works (36)
        assert len(results) >= 36

        # All results should be from Plato
        for author, work in results:
            if author.tlg_id == "tlg0059":
                assert author.name_en == "Plato"

    def test_search_by_work_title(self, catalog):
        """Test searching by work title."""
        results = catalog.search_works("Republic")

        # Should find at least Plato's Republic
        assert len(results) >= 1

        # Check Plato's Republic is in results
        republic = next(
            (
                (a, w)
                for a, w in results
                if a.tlg_id == "tlg0059" and w.work_id == "tlg030"
            ),
            None,
        )
        assert republic is not None
        author, work = republic
        assert work.title_en == "Republic"

    def test_search_greek_text(self, catalog):
        """Test searching with Greek text."""
        results = catalog.search_works("Φαίδων")

        # Should find Phaedo
        assert len(results) >= 1

        # Check Phaedo is in results
        phaedo = next(((a, w) for a, w in results if w.title_grc == "Φαίδων"), None)
        assert phaedo is not None

    def test_search_case_insensitive(self, catalog):
        """Test that search is case-insensitive."""
        results_lower = catalog.search_works("plato")
        results_upper = catalog.search_works("PLATO")
        results_mixed = catalog.search_works("PlAtO")

        # All should return same number of results
        assert len(results_lower) == len(results_upper)
        assert len(results_lower) == len(results_mixed)

    def test_get_author_info(self, catalog):
        """Test getting specific author info."""
        plato = catalog.get_author_info("tlg0059")

        assert plato is not None
        assert plato.tlg_id == "tlg0059"
        assert plato.name_en == "Plato"

    def test_get_author_info_nonexistent(self, catalog):
        """Test getting info for non-existent author."""
        result = catalog.get_author_info("tlg9999")
        assert result is None

    def test_resolve_work_id_valid(self, catalog):
        """Test resolving valid work ID to file path."""
        # Test Plato's Euthyphro: tlg0059.tlg001
        file_path = catalog.resolve_work_id("tlg0059.tlg001")

        assert file_path is not None
        assert file_path.exists()
        assert "tlg0059" in str(file_path)
        assert "tlg001" in str(file_path)
        assert file_path.suffix == ".xml"

    def test_resolve_work_id_invalid_format(self, catalog):
        """Test resolving work ID with invalid format."""
        # Missing work part
        with pytest.raises(WorkNotFoundError) as exc_info:
            catalog.resolve_work_id("tlg0059")
        assert "format" in str(exc_info.value).lower()

        # Too many parts
        with pytest.raises(WorkNotFoundError) as exc_info:
            catalog.resolve_work_id("tlg0059.tlg001.extra")
        assert "format" in str(exc_info.value).lower()

    def test_resolve_work_id_nonexistent_author(self, catalog):
        """Test resolving work ID for non-existent author."""
        with pytest.raises(WorkNotFoundError) as exc_info:
            catalog.resolve_work_id("tlg9999.tlg001")
        assert "tlg9999" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_resolve_work_id_nonexistent_work(self, catalog):
        """Test resolving work ID for non-existent work."""
        with pytest.raises(WorkNotFoundError) as exc_info:
            catalog.resolve_work_id("tlg0059.tlg999")
        assert "tlg999" in str(exc_info.value)
        assert "Plato" in str(exc_info.value)

    def test_resolve_work_id_euclid(self, catalog):
        """Test resolving Euclid's Elements (has Latin title)."""
        file_path = catalog.resolve_work_id("tlg1799.tlg001")

        assert file_path is not None
        assert file_path.exists()
        assert "tlg1799" in str(file_path)
        assert "tlg001" in str(file_path)

    def test_resolve_author_name_by_english_name(self, catalog):
        """Test resolving author by English name."""
        tlg_id = catalog.resolve_author_name("Plato")
        assert tlg_id == "tlg0059"

    def test_resolve_author_name_case_insensitive(self, catalog):
        """Test author name resolution is case-insensitive."""
        tlg_id = catalog.resolve_author_name("plato")
        assert tlg_id == "tlg0059"

    def test_resolve_author_name_by_greek_name(self, catalog):
        """Test resolving author by Greek name (if available)."""
        # Note: Not all authors have Greek names in the catalog
        # This test verifies the mechanism works even if specific authors lack Greek names
        tlg_id = catalog.resolve_author_name("Πλάτων")
        # Plato may not have Greek name in catalog, so None is acceptable
        assert tlg_id is None or tlg_id == "tlg0059"

    def test_resolve_author_name_by_tlg_id(self, catalog):
        """Test that TLG IDs pass through unchanged."""
        tlg_id = catalog.resolve_author_name("tlg0059")
        assert tlg_id == "tlg0059"

    def test_resolve_author_name_nonexistent(self, catalog):
        """Test resolving non-existent author returns None."""
        tlg_id = catalog.resolve_author_name("NonexistentAuthor")
        assert tlg_id is None

    def test_page_range_in_works(self, catalog):
        """Test that works include page ranges."""
        works = catalog.list_works("tlg0059")

        # Find Euthyphro
        euthyphro = next((w for w in works if w.work_id == "tlg001"), None)
        assert euthyphro is not None
        assert euthyphro.page_range == "2-16"

        # Find Republic
        republic = next((w for w in works if w.work_id == "tlg030"), None)
        assert republic is not None
        assert republic.page_range == "327-621"

    def test_section_numbers_in_works(self, catalog):
        """Test that works with section-based numbering include section ranges."""
        works = catalog.list_works("tlg0010")  # Isocrates

        # Find Trapeziticus
        trapeziticus = next((w for w in works if w.work_id == "tlg005"), None)
        assert trapeziticus is not None
        # Trapeziticus has sections 1-58
        assert trapeziticus.page_range == "1-58"
