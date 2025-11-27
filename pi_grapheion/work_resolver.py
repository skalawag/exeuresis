"""Work name resolution with alias support."""

import logging
from pathlib import Path
from typing import Dict, Optional
import yaml

from pi_grapheion.catalog import PerseusCatalog
from pi_grapheion.exceptions import WorkNotFoundError

logger = logging.getLogger(__name__)


class WorkResolver:
    """Resolve work names to TLG IDs using aliases and catalog lookup."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        user_config_path: Optional[Path] = None,
        project_config_path: Optional[Path] = None,
    ):
        """
        Initialize WorkResolver with optional config paths.

        Args:
            config_path: Single config file (for testing)
            user_config_path: User config (~/.pi-grapheion/aliases.yaml)
            project_config_path: Project config (.pi-grapheion/aliases.yaml)
        """
        self.catalog = PerseusCatalog()
        self.aliases: Dict[str, str] = {}

        # Load aliases in order: extracted, user, project (project overrides)
        self._load_extracted_aliases()

        if config_path:
            # Single config for testing
            self._load_config_file(config_path)
        else:
            # Load user config first
            if user_config_path:
                self._load_config_file(user_config_path)
            elif Path.home().joinpath(".pi-grapheion", "aliases.yaml").exists():
                self._load_config_file(
                    Path.home() / ".pi-grapheion" / "aliases.yaml"
                )

            # Load project config second (overrides user)
            if project_config_path:
                self._load_config_file(project_config_path)
            elif Path(".pi-grapheion/aliases.yaml").exists():
                self._load_config_file(Path(".pi-grapheion/aliases.yaml"))

    def resolve(self, name: str) -> str:
        """
        Resolve a work name to TLG ID.

        Args:
            name: Work name (title, alias, or TLG ID)

        Returns:
            TLG ID (e.g., "tlg0059.tlg001")

        Raises:
            WorkNotFoundError: If name cannot be resolved
        """
        # If already a valid TLG ID, pass through
        if self._is_tlg_id(name):
            return name

        # Try aliases (case-insensitive)
        name_lower = name.lower()
        if name_lower in self.aliases:
            return self.aliases[name_lower]

        # Not found
        raise WorkNotFoundError(
            name,
            f"Could not resolve work name '{name}'. "
            f"Try using the full TLG ID (e.g., tlg0059.tlg001) or check available aliases."
        )

    def _is_tlg_id(self, name: str) -> bool:
        """Check if name is already a TLG ID format."""
        # Format: tlg####.tlg###
        if "." not in name:
            return False
        parts = name.split(".")
        if len(parts) != 2:
            return False
        return parts[0].startswith("tlg") and parts[1].startswith("tlg")

    def _load_extracted_aliases(self):
        """Extract aliases from catalog (titles and common abbreviations)."""
        try:
            authors = self.catalog.list_authors()
            for author in authors:
                works = self.catalog.list_works(author.tlg_id)
                for work in works:
                    work_id = f"{work.tlg_id}.{work.work_id}"

                    # Add English title as alias (case-insensitive)
                    if work.title_en:
                        self.aliases[work.title_en.lower()] = work_id

                    # Add Greek title as alias
                    if work.title_grc:
                        self.aliases[work.title_grc.lower()] = work_id

        except Exception as e:
            logger.warning(f"Failed to extract aliases from catalog: {e}")

    def _load_config_file(self, config_path: Path):
        """Load aliases from YAML config file."""
        try:
            if not config_path.exists():
                return

            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if config and "aliases" in config:
                for alias, work_id in config["aliases"].items():
                    # Store as lowercase for case-insensitive lookup
                    self.aliases[alias.lower()] = work_id

        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
