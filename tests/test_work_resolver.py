"""Tests for work name resolution and aliases."""

import pytest
from pathlib import Path
from exeuresis.work_resolver import WorkResolver
from exeuresis.exceptions import WorkNotFoundError


class TestWorkResolver:
    """Tests for WorkResolver alias system."""

    def test_resolve_exact_tlg_id(self):
        """Test resolving exact TLG ID passes through."""
        resolver = WorkResolver()
        assert resolver.resolve("tlg0059.tlg001") == "tlg0059.tlg001"

    def test_resolve_work_by_english_title(self):
        """Test resolving work by English title."""
        resolver = WorkResolver()
        # Case-insensitive
        assert resolver.resolve("euthyphro") == "tlg0059.tlg001"
        assert resolver.resolve("Euthyphro") == "tlg0059.tlg001"
        assert resolver.resolve("EUTHYPHRO") == "tlg0059.tlg001"

    def test_resolve_work_by_greek_title(self):
        """Test resolving work by Greek title."""
        resolver = WorkResolver()
        result = resolver.resolve("Εὐθύφρων")
        assert result == "tlg0059.tlg001"

    def test_resolve_work_with_extracted_alias(self):
        """Test resolving work using extracted alias."""
        resolver = WorkResolver()
        # "Republic" should resolve
        result = resolver.resolve("republic")
        assert result == "tlg0059.tlg030"

    def test_resolve_ambiguous_name_raises_error(self):
        """Test ambiguous name raises error with suggestions."""
        resolver = WorkResolver()
        with pytest.raises(WorkNotFoundError) as exc_info:
            # If there are multiple matches, should fail
            resolver.resolve("nonexistent_work")
        assert "nonexistent_work" in str(exc_info.value)

    def test_resolve_with_user_config(self, tmp_path):
        """Test user-defined aliases from config file."""
        # Create test config
        config_file = tmp_path / "aliases.yaml"
        config_file.write_text("""
aliases:
  euth: tlg0059.tlg001
  rep: tlg0059.tlg030
""")

        resolver = WorkResolver(config_path=config_file)
        assert resolver.resolve("euth") == "tlg0059.tlg001"
        assert resolver.resolve("rep") == "tlg0059.tlg030"

    def test_project_config_overrides_user_config(self, tmp_path):
        """Test project config overrides user config."""
        user_config = tmp_path / "user_aliases.yaml"
        user_config.write_text("""
aliases:
  mywork: tlg0059.tlg001
""")

        project_config = tmp_path / "project_aliases.yaml"
        project_config.write_text("""
aliases:
  mywork: tlg0059.tlg030  # Override
""")

        resolver = WorkResolver(
            user_config_path=user_config,
            project_config_path=project_config
        )
        # Project config should override
        assert resolver.resolve("mywork") == "tlg0059.tlg030"
