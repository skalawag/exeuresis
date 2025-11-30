"""Configuration management for exeuresis."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class CorpusConfig:
    """Configuration for a single corpus."""

    name: str
    path: Path
    description: Optional[str] = None


def get_corpora() -> Dict[str, CorpusConfig]:
    """
    Get all configured corpora.

    Returns:
        Dictionary mapping corpus names to CorpusConfig objects

    Examples:
        >>> corpora = get_corpora()
        >>> corpora['main'].path
        Path('/home/user/canonical-greekLit/data')
    """
    corpora = {}

    # 1. Check environment variable (creates "default" corpus)
    env_path = os.environ.get("PERSEUS_CORPUS_PATH")
    if env_path:
        corpora["default"] = CorpusConfig(
            name="default",
            path=Path(env_path),
            description="From PERSEUS_CORPUS_PATH environment variable",
        )
        return corpora

    # 2. Check project config
    project_config = Path(".exeuresis") / "config.yaml"
    corpora = _load_corpora_from_config(project_config)
    if corpora:
        return corpora

    # 3. Check user config
    user_config = Path.home() / ".exeuresis" / "config.yaml"
    corpora = _load_corpora_from_config(user_config)
    if corpora:
        return corpora

    # 4. Default: single corpus named "default"
    project_root = Path(__file__).parent.parent
    default_path = project_root / "canonical-greekLit" / "data"
    corpora["default"] = CorpusConfig(
        name="default", path=default_path, description="Default Perseus Greek corpus"
    )

    return corpora


def get_default_corpus_name() -> str:
    """
    Get the name of the default corpus from configuration.

    Returns:
        Name of the default corpus (defaults to "default" if not specified)

    Examples:
        >>> get_default_corpus_name()
        'main'  # if config specifies default_corpus: main
    """
    # Check environment variable (always "default")
    if os.environ.get("PERSEUS_CORPUS_PATH"):
        return "default"

    # Check project config
    project_config = Path(".exeuresis") / "config.yaml"
    default_name = _load_default_corpus_name(project_config)
    if default_name:
        return default_name

    # Check user config
    user_config = Path.home() / ".exeuresis" / "config.yaml"
    default_name = _load_default_corpus_name(user_config)
    if default_name:
        return default_name

    # Default
    return "default"


def get_corpus_path(corpus_name: Optional[str] = None) -> Path:
    """
    Get Perseus corpus path from configuration with fallback to default.

    Args:
        corpus_name: Name of corpus to use (uses default if None)

    Returns:
        Path to the corpus data directory

    Raises:
        KeyError: If corpus_name is specified but not found in config

    Examples:
        >>> # Get default corpus
        >>> get_corpus_path()
        Path('.../canonical-greekLit/data')

        >>> # Get specific corpus
        >>> get_corpus_path('dev')
        Path('.../test-fixtures/mini-corpus')
    """
    # Get all corpora
    corpora = get_corpora()

    # If no corpus_name specified, use default
    if corpus_name is None:
        corpus_name = get_default_corpus_name()

    # Look up the corpus
    if corpus_name not in corpora:
        available = ", ".join(corpora.keys())
        raise KeyError(
            f"Corpus '{corpus_name}' not found. " f"Available corpora: {available}"
        )

    return corpora[corpus_name].path


def _load_corpora_from_config(config_file: Path) -> Dict[str, CorpusConfig]:
    """
    Load corpora configuration from a YAML config file.

    Supports both old single-corpus format (corpus_path) and new multi-corpus
    format (corpora section).

    Args:
        config_file: Path to config file

    Returns:
        Dictionary of corpus name -> CorpusConfig, or empty dict if none found
    """
    if not config_file.exists():
        return {}

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config:
            return {}

        corpora = {}
        project_root = Path(__file__).parent.parent

        # Check for new multi-corpus format
        if "corpora" in config and config["corpora"]:
            for name, corpus_config in config["corpora"].items():
                if not corpus_config or "path" not in corpus_config:
                    logger.warning(f"Corpus '{name}' missing path, skipping")
                    continue

                path_str = corpus_config["path"]
                path = Path(path_str)

                # Resolve relative paths from project root
                if not path.is_absolute():
                    path = (project_root / path).resolve()

                description = corpus_config.get("description")
                corpora[name] = CorpusConfig(
                    name=name, path=path, description=description
                )

            return corpora

        # Check for old single-corpus format (backward compatibility)
        if "corpus_path" in config:
            corpus_path_str = config["corpus_path"]
            if corpus_path_str:
                path = Path(corpus_path_str)

                # Resolve relative paths from project root
                if not path.is_absolute():
                    path = (project_root / path).resolve()

                corpora["default"] = CorpusConfig(
                    name="default", path=path, description="Single corpus from config"
                )
                return corpora

        return {}

    except Exception as e:
        logger.warning(f"Failed to load config from {config_file}: {e}")
        return {}


def _load_default_corpus_name(config_file: Path) -> Optional[str]:
    """
    Load default_corpus name from config file.

    Args:
        config_file: Path to config file

    Returns:
        Name of default corpus, or None if not specified
    """
    if not config_file.exists():
        return None

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config:
            return None

        return config.get("default_corpus")

    except Exception as e:
        logger.warning(f"Failed to load default corpus name from {config_file}: {e}")
        return None


def _load_corpus_path_from_config(config_file: Path) -> Optional[Path]:
    """
    Load corpus_path from a YAML config file (old single-corpus format).

    This function is kept for backward compatibility but now delegates to
    _load_corpora_from_config().

    Args:
        config_file: Path to config file

    Returns:
        Path object if corpus_path is found and valid, None otherwise
    """
    corpora = _load_corpora_from_config(config_file)
    if "default" in corpora:
        return corpora["default"].path
    return None
