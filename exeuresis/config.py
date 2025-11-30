"""Configuration management for exeuresis."""

import logging
import os
from pathlib import Path
from typing import Optional
import yaml

logger = logging.getLogger(__name__)


def get_corpus_path() -> Path:
    """
    Get Perseus corpus path from configuration with fallback to default.

    Priority order (highest to lowest):
    1. Environment variable PERSEUS_CORPUS_PATH
    2. Project config (.exeuresis/config.yaml)
    3. User config (~/.exeuresis/config.yaml)
    4. Default: canonical-greekLit/data relative to project root

    Returns:
        Path to the corpus data directory

    Examples:
        >>> # With environment variable set
        >>> os.environ['PERSEUS_CORPUS_PATH'] = '/custom/path'
        >>> get_corpus_path()
        Path('/custom/path')

        >>> # With config file
        >>> # .exeuresis/config.yaml contains: corpus_path: /my/corpus
        >>> get_corpus_path()
        Path('/my/corpus')

        >>> # Default fallback
        >>> get_corpus_path()
        Path('.../canonical-greekLit/data')
    """
    # 1. Check environment variable (highest priority)
    env_path = os.environ.get('PERSEUS_CORPUS_PATH')
    if env_path:
        path = Path(env_path)
        logger.debug(f"Using corpus path from PERSEUS_CORPUS_PATH: {path}")
        return path

    # 2. Check project config (.exeuresis/config.yaml)
    project_config = Path('.exeuresis') / 'config.yaml'
    corpus_path = _load_corpus_path_from_config(project_config)
    if corpus_path:
        logger.debug(f"Using corpus path from project config: {corpus_path}")
        return corpus_path

    # 3. Check user config (~/.exeuresis/config.yaml)
    user_config = Path.home() / '.exeuresis' / 'config.yaml'
    corpus_path = _load_corpus_path_from_config(user_config)
    if corpus_path:
        logger.debug(f"Using corpus path from user config: {corpus_path}")
        return corpus_path

    # 4. Default: canonical-greekLit/data relative to project root
    # Project root is parent of exeuresis package directory
    project_root = Path(__file__).parent.parent
    default_path = project_root / 'canonical-greekLit' / 'data'
    logger.debug(f"Using default corpus path: {default_path}")
    return default_path


def _load_corpus_path_from_config(config_file: Path) -> Optional[Path]:
    """
    Load corpus_path from a YAML config file.

    Args:
        config_file: Path to config file

    Returns:
        Path object if corpus_path is found and valid, None otherwise
    """
    if not config_file.exists():
        return None

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not config or 'corpus_path' not in config:
            return None

        corpus_path_str = config['corpus_path']
        if not corpus_path_str:
            return None

        # Convert to Path
        corpus_path = Path(corpus_path_str)

        # If relative, resolve from project root
        if not corpus_path.is_absolute():
            project_root = Path(__file__).parent.parent
            corpus_path = (project_root / corpus_path).resolve()

        return corpus_path

    except Exception as e:
        logger.warning(f"Failed to load config from {config_file}: {e}")
        return None
