"""SoftwareRegistry implementation using marketplace YAML catalog."""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
_CATALOG_PATH = _ROOT / "marketplace" / "softwares" / "catalog.yaml"


class YamlSoftwareRegistry:
    """SoftwareRegistry implementation loading from marketplace YAML catalog."""

    def __init__(self, catalog_path: Path | None = None) -> None:
        self._catalog_path = catalog_path or _CATALOG_PATH

    def list_entries(self) -> list[dict[str, Any]]:
        """Return all catalog entries. Each has id, name, author, description, etc."""
        if not self._catalog_path.exists():
            logger.warning(f"Software catalog not found at {self._catalog_path}")
            return []
        try:
            raw = self._catalog_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            if not isinstance(data, list):
                logger.warning("Software catalog root is not a list")
                return []
            return data
        except (yaml.YAMLError, OSError) as e:
            logger.warning(f"Failed to load software catalog: {e}")
            return []

    def get_entry(self, software_id: str) -> dict[str, Any] | None:
        """Return a single catalog entry by id, or None if not found."""
        for entry in self.list_entries():
            if entry.get("id") == software_id:
                return entry
        return None
