"""Tests for configuration management."""

import os
from pathlib import Path

import yaml

from exeuresis.config import _load_corpus_path_from_config, get_corpus_path


class TestGetCorpusPath:
    """Tests for get_corpus_path function."""

    def test_default_path(self, monkeypatch):
        """Test default path when no config is set."""
        # Clear environment variable
        monkeypatch.delenv("PERSEUS_CORPUS_PATH", raising=False)

        # Mock config files to not exist
        monkeypatch.setattr(Path, "exists", lambda self: False)

        # Get path - should return default
        path = get_corpus_path()

        # Should be canonical-greekLit/data relative to project root
        assert path.name == "data"
        assert path.parent.name == "canonical-greekLit"

    def test_environment_variable_override(self, monkeypatch):
        """Test that environment variable takes highest priority."""
        custom_path = "/custom/perseus/path"
        monkeypatch.setenv("PERSEUS_CORPUS_PATH", custom_path)

        path = get_corpus_path()

        assert path == Path(custom_path)

    def test_project_config_priority(self, monkeypatch, tmp_path):
        """Test that project config takes priority over user config."""
        # Clear environment variable
        monkeypatch.delenv("PERSEUS_CORPUS_PATH", raising=False)

        # Write different paths
        project_path = "/project/corpus"
        user_path = "/user/corpus"

        # Create project directory and config
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / ".exeuresis" / "config.yaml"
        project_config.parent.mkdir(parents=True)
        with open(project_config, "w") as f:
            yaml.dump({"corpus_path": project_path}, f)

        # Create user config in different location
        user_home = tmp_path / "home"
        user_home.mkdir()
        user_config = user_home / ".exeuresis" / "config.yaml"
        user_config.parent.mkdir(parents=True)
        with open(user_config, "w") as f:
            yaml.dump({"corpus_path": user_path}, f)

        # Mock Path.home() to return our test home
        monkeypatch.setattr(Path, "home", lambda: user_home)

        # Change to project directory for project config
        original_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            path = get_corpus_path()

            # Project config should win
            assert str(path) == project_path
        finally:
            os.chdir(original_cwd)

    def test_user_config_fallback(self, monkeypatch, tmp_path):
        """Test that user config is used when project config doesn't exist."""
        # Clear environment variable
        monkeypatch.delenv("PERSEUS_CORPUS_PATH", raising=False)

        # Create user config
        user_config = tmp_path / ".exeuresis" / "config.yaml"
        user_config.parent.mkdir(parents=True)
        user_path = "/user/corpus"

        with open(user_config, "w") as f:
            yaml.dump({"corpus_path": user_path}, f)

        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock project config to not exist
        original_cwd = os.getcwd()
        # Change to a temp dir where .exeuresis/config.yaml doesn't exist
        temp_project = tmp_path / "project"
        temp_project.mkdir()
        os.chdir(temp_project)

        try:
            path = get_corpus_path()

            # User config should be used
            assert str(path) == user_path
        finally:
            os.chdir(original_cwd)


class TestLoadCorpusPathFromConfig:
    """Tests for _load_corpus_path_from_config function."""

    def test_missing_config_file(self, tmp_path):
        """Test handling of missing config file."""
        config_file = tmp_path / "nonexistent.yaml"

        result = _load_corpus_path_from_config(config_file)

        assert result is None

    def test_config_without_corpus_path(self, tmp_path):
        """Test handling of config file without corpus_path key."""
        config_file = tmp_path / "config.yaml"

        with open(config_file, "w") as f:
            yaml.dump({"other_key": "value"}, f)

        result = _load_corpus_path_from_config(config_file)

        assert result is None

    def test_absolute_path(self, tmp_path):
        """Test handling of absolute path in config."""
        config_file = tmp_path / "config.yaml"
        corpus_path = "/absolute/path/to/corpus"

        with open(config_file, "w") as f:
            yaml.dump({"corpus_path": corpus_path}, f)

        result = _load_corpus_path_from_config(config_file)

        assert result == Path(corpus_path)

    def test_relative_path(self, tmp_path):
        """Test handling of relative path in config."""
        config_file = tmp_path / "config.yaml"

        with open(config_file, "w") as f:
            yaml.dump({"corpus_path": "../relative/path"}, f)

        result = _load_corpus_path_from_config(config_file)

        # Should be resolved relative to project root
        assert result is not None
        assert result.is_absolute()

    def test_empty_corpus_path(self, tmp_path):
        """Test handling of empty corpus_path value."""
        config_file = tmp_path / "config.yaml"

        with open(config_file, "w") as f:
            yaml.dump({"corpus_path": ""}, f)

        result = _load_corpus_path_from_config(config_file)

        assert result is None

    def test_malformed_yaml(self, tmp_path):
        """Test handling of malformed YAML file."""
        config_file = tmp_path / "config.yaml"

        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        result = _load_corpus_path_from_config(config_file)

        # Should return None and log warning
        assert result is None


class TestConfigIntegration:
    """Integration tests for configuration system."""

    def test_catalog_uses_config(self, monkeypatch, tmp_path):
        """Test that PerseusCatalog uses config path."""
        from exeuresis.catalog import PerseusCatalog

        # Create a test corpus directory
        custom_path = tmp_path / "custom_corpus"
        custom_path.mkdir()

        monkeypatch.setenv("PERSEUS_CORPUS_PATH", str(custom_path))

        catalog = PerseusCatalog()

        assert catalog.data_dir == custom_path

    def test_anthology_extractor_uses_config(self, monkeypatch, tmp_path):
        """Test that AnthologyExtractor uses config path."""
        from exeuresis.anthology_extractor import AnthologyExtractor

        # Create a test corpus directory (AnthologyExtractor doesn't validate existence)
        custom_path = tmp_path / "custom_corpus"
        custom_path.mkdir()

        monkeypatch.setenv("PERSEUS_CORPUS_PATH", str(custom_path))

        extractor = AnthologyExtractor()

        assert extractor.data_dir == custom_path
