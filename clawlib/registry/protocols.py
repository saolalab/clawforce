"""Abstract protocols for Skill, MCP, and Software registries.

APIs and workers depend on these protocols, not concrete implementations.
Swap implementations via config (SKILL_REGISTRY env).
"""

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SkillRegistry(Protocol):
    """Protocol for skill marketplace search and install."""

    async def search_skills(self, query: str, limit: int) -> list[dict]:
        """Search for skills. Returns list of dicts with slug, name, description, etc."""
        ...

    async def install_skill(
        self,
        slug: str,
        dest: Path,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        """Install a skill into dest. Returns (returncode, stdout, stderr)."""
        ...


@runtime_checkable
class MCPRegistry(Protocol):
    """Protocol for MCP server marketplace search and details."""

    async def search_mcp_servers(self, query: str, limit: int) -> list[dict]:
        """Search for MCP servers. Returns list of dicts with id, name, description, etc."""
        ...

    async def get_mcp_server(self, slug: str) -> dict | None:
        """Get details for a specific MCP server. Returns dict or None if not found."""
        ...


@runtime_checkable
class SoftwareRegistry(Protocol):
    """Protocol for software catalog list and lookup."""

    def list_entries(self) -> list[dict[str, Any]]:
        """Return all catalog entries. Each has id, name, author, description, etc."""
        ...

    def get_entry(self, software_id: str) -> dict[str, Any] | None:
        """Return a single catalog entry by id, or None if not found."""
        ...
