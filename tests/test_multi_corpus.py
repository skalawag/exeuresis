"""Tests for multi-corpus configuration."""

import os
from pathlib import Path
import pytest
import yaml

from exeuresis.config import (
    get_corpora,
    get_default_corpus_name,
    get_corpus_path,
    CorpusConfig
)


class TestMultiCorpusConfig:
    """Tests for multi-corpus configuration loading."""

    def test_multi_corpus_from_config(self, monkeypatch, tmp_path):
        """Test loading multiple corpora from config file."""
        # Clear environment variable
        monkeypatch.delenv('PERSEUS_CORPUS_PATH', raising=False)

        # Create multi-corpus config
        project_dir = tmp_path / 'project'
        project_dir.mkdir()
        config_file = project_dir / '.exeuresis' / 'config.yaml'
        config_file.parent.mkdir(parents=True)

        config = {
            'corpora': {
                'main': {
                    'path': '/corpus/main',
                    'description': 'Main corpus'
                },
                'dev': {
                    'path': './test-corpus',
                    'description': 'Test corpus'
                }
            },
            'default_corpus': 'main'
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            corpora = get_corpora()

            assert len(corpora) == 2
            assert 'main' in corpora
            assert 'dev' in corpora

            assert corpora['main'].name == 'main'
            assert corpora['main'].path == Path('/corpus/main')
            assert corpora['main'].description == 'Main corpus'

            # Relative path should be resolved
            assert corpora['dev'].name == 'dev'
            assert corpora['dev'].path.is_absolute()
            assert corpora['dev'].description == 'Test corpus'
        finally:
            os.chdir(original_cwd)

    def test_default_corpus_name(self, monkeypatch, tmp_path):
        """Test retrieving default corpus name."""
        # Clear environment variable
        monkeypatch.delenv('PERSEUS_CORPUS_PATH', raising=False)

        # Create config with default_corpus
        project_dir = tmp_path / 'project'
        project_dir.mkdir()
        config_file = project_dir / '.exeuresis' / 'config.yaml'
        config_file.parent.mkdir(parents=True)

        config = {
            'corpora': {
                'main': {'path': '/corpus/main'},
                'dev': {'path': '/corpus/dev'}
            },
            'default_corpus': 'dev'
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        original_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            default_name = get_default_corpus_name()
            assert default_name == 'dev'
        finally:
            os.chdir(original_cwd)

    def test_get_corpus_path_with_name(self, monkeypatch, tmp_path):
        """Test getting path for specific corpus."""
        # Clear environment variable
        monkeypatch.delenv('PERSEUS_CORPUS_PATH', raising=False)

        # Create multi-corpus config
        project_dir = tmp_path / 'project'
        project_dir.mkdir()
        config_file = project_dir / '.exeuresis' / 'config.yaml'
        config_file.parent.mkdir(parents=True)

        config = {
            'corpora': {
                'main': {'path': '/corpus/main'},
                'dev': {'path': '/corpus/dev'}
            },
            'default_corpus': 'main'
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        original_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            # Get specific corpus
            main_path = get_corpus_path('main')
            assert main_path == Path('/corpus/main')

            dev_path = get_corpus_path('dev')
            assert dev_path == Path('/corpus/dev')

            # Get default corpus (None)
            default_path = get_corpus_path()
            assert default_path == Path('/corpus/main')
        finally:
            os.chdir(original_cwd)

    def test_get_corpus_path_invalid_name(self, monkeypatch, tmp_path):
        """Test error when requesting non-existent corpus."""
        # Clear environment variable
        monkeypatch.delenv('PERSEUS_CORPUS_PATH', raising=False)

        # Create config
        project_dir = tmp_path / 'project'
        project_dir.mkdir()
        config_file = project_dir / '.exeuresis' / 'config.yaml'
        config_file.parent.mkdir(parents=True)

        config = {
            'corpora': {
                'main': {'path': '/corpus/main'}
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        original_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            with pytest.raises(KeyError) as exc_info:
                get_corpus_path('nonexistent')

            assert 'nonexistent' in str(exc_info.value)
            assert 'Available corpora: main' in str(exc_info.value)
        finally:
            os.chdir(original_cwd)

    def test_backward_compat_single_corpus_path(self, monkeypatch, tmp_path):
        """Test backward compatibility with old corpus_path format."""
        # Clear environment variable
        monkeypatch.delenv('PERSEUS_CORPUS_PATH', raising=False)

        # Create old-style config
        project_dir = tmp_path / 'project'
        project_dir.mkdir()
        config_file = project_dir / '.exeuresis' / 'config.yaml'
        config_file.parent.mkdir(parents=True)

        config = {'corpus_path': '/old/corpus/path'}

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        original_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            corpora = get_corpora()

            # Should create single 'default' corpus
            assert len(corpora) == 1
            assert 'default' in corpora
            assert corpora['default'].path == Path('/old/corpus/path')
            assert corpora['default'].description == 'Single corpus from config'

            # get_corpus_path() should work
            path = get_corpus_path()
            assert path == Path('/old/corpus/path')
        finally:
            os.chdir(original_cwd)

    def test_env_var_creates_default_corpus(self, monkeypatch):
        """Test that environment variable creates 'default' corpus."""
        monkeypatch.setenv('PERSEUS_CORPUS_PATH', '/env/corpus')

        corpora = get_corpora()

        assert len(corpora) == 1
        assert 'default' in corpora
        assert corpora['default'].path == Path('/env/corpus')
        assert 'environment variable' in corpora['default'].description.lower()

        # Default name should be 'default'
        assert get_default_corpus_name() == 'default'

        # get_corpus_path() should return env path
        assert get_corpus_path() == Path('/env/corpus')


class TestCatalogWithCorpusName:
    """Tests for PerseusCatalog with corpus_name parameter."""

    def test_catalog_with_corpus_name(self, monkeypatch, tmp_path):
        """Test that catalog uses specified corpus."""
        from exeuresis.catalog import PerseusCatalog

        # Create test corpora directories
        main_corpus = tmp_path / 'main_corpus'
        dev_corpus = tmp_path / 'dev_corpus'
        main_corpus.mkdir()
        dev_corpus.mkdir()

        # Create project with multi-corpus config
        project_dir = tmp_path / 'project'
        project_dir.mkdir()
        config_file = project_dir / '.exeuresis' / 'config.yaml'
        config_file.parent.mkdir(parents=True)

        config = {
            'corpora': {
                'main': {'path': str(main_corpus)},
                'dev': {'path': str(dev_corpus)}
            },
            'default_corpus': 'main'
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        original_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            # Create catalog with specific corpus
            catalog_main = PerseusCatalog(corpus_name='main')
            assert catalog_main.data_dir == main_corpus
            assert catalog_main.corpus_name == 'main'

            catalog_dev = PerseusCatalog(corpus_name='dev')
            assert catalog_dev.data_dir == dev_corpus
            assert catalog_dev.corpus_name == 'dev'

            # Create catalog with no corpus_name (uses default)
            catalog_default = PerseusCatalog()
            assert catalog_default.data_dir == main_corpus
            assert catalog_default.corpus_name == 'main'
        finally:
            os.chdir(original_cwd)

    def test_catalog_with_explicit_data_dir(self, tmp_path):
        """Test that explicit data_dir overrides corpus_name."""
        from exeuresis.catalog import PerseusCatalog

        custom_dir = tmp_path / 'custom'
        custom_dir.mkdir()

        catalog = PerseusCatalog(data_dir=custom_dir, corpus_name='ignored')
        assert catalog.data_dir == custom_dir
        assert catalog.corpus_name == 'custom'


class TestWorkResolverWithCorpusName:
    """Tests for WorkResolver with corpus_name parameter."""

    def test_work_resolver_corpus_name(self, monkeypatch, tmp_path):
        """Test that WorkResolver passes corpus_name to catalog."""
        from exeuresis.work_resolver import WorkResolver

        # Create test corpus
        corpus_dir = tmp_path / 'corpus'
        corpus_dir.mkdir()

        monkeypatch.setenv('PERSEUS_CORPUS_PATH', str(corpus_dir))

        resolver = WorkResolver(corpus_name='default')
        assert resolver.catalog.corpus_name == 'default'
        assert resolver.corpus_name == 'default'


class TestAnthologyExtractorWithCorpusName:
    """Tests for AnthologyExtractor with corpus_name parameter."""

    def test_anthology_extractor_corpus_name(self, monkeypatch, tmp_path):
        """Test that AnthologyExtractor passes corpus_name to catalog."""
        from exeuresis.anthology_extractor import AnthologyExtractor

        # Create test corpus
        corpus_dir = tmp_path / 'corpus'
        corpus_dir.mkdir()

        monkeypatch.setenv('PERSEUS_CORPUS_PATH', str(corpus_dir))

        extractor = AnthologyExtractor(corpus_name='default')
        assert extractor.catalog.corpus_name == 'default'
        assert extractor.corpus_name == 'default'
        assert extractor.data_dir == corpus_dir
