"""Async HTTP client for the official MCP Registry (registry.modelcontextprotocol.io)."""

import logging
from urllib.parse import urlencode

import httpx

from clawlib.mcpregistry.models import MCPServerInfo

logger = logging.getLogger(__name__)

_REGISTRY_BASE_URL = "https://registry.modelcontextprotocol.io/v0/servers"
_TIMEOUT = 15


class MCPRegistryClient:
    """Async client for the official MCP Registry.

    Uses the public REST API at registry.modelcontextprotocol.io/v0/.
    No authentication required for read operations.
    """

    def __init__(self, base_url: str = _REGISTRY_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    async def search(
        self,
        query: str = "",
        limit: int = 50,
    ) -> list[MCPServerInfo]:
        """Search the MCP Registry for servers.

        Args:
            query: Search term (empty returns all/popular servers)
            limit: Maximum results to return

        Returns:
            List of MCPServerInfo objects (latest version only, deduplicated)
        """
        params: dict[str, str | int] = {"limit": limit, "version": "latest"}
        if query.strip():
            params["search"] = query.strip()

        url = f"{self.base_url}?{urlencode(params)}"

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            logger.warning("MCP Registry request timed out")
            return []
        except httpx.HTTPStatusError as e:
            logger.warning(f"MCP Registry HTTP error: {e}")
            return []
        except Exception as e:
            logger.warning(f"MCP Registry request failed: {e}")
            return []

        return self._parse_response(data)

    async def get_server(self, server_id: str) -> MCPServerInfo | None:
        """Get details for a specific MCP server.

        Args:
            server_id: The server identifier (e.g., "@modelcontextprotocol/server-filesystem")

        Returns:
            MCPServerInfo or None if not found
        """
        url = f"{self.base_url}/{server_id}"

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url)
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning(f"MCP Registry get_server failed: {e}")
            return None

        return self._parse_server(data)

    def _parse_response(self, data: dict | list) -> list[MCPServerInfo]:
        """Parse the registry API response into MCPServerInfo objects."""
        servers = data.get("servers", []) if isinstance(data, dict) else data
        results = []
        for item in servers:
            if not item:
                continue
            server_data = item.get("server", item) if isinstance(item, dict) else item
            meta = item.get("_meta", {}) if isinstance(item, dict) else {}
            try:
                results.append(self._parse_server(server_data, meta))
            except Exception:
                logger.debug(f"Skipping unparseable registry entry: {server_data.get('name', '?')}")
        return results

    def _parse_server(self, s: dict, meta: dict | None = None) -> MCPServerInfo:
        """Parse a single server entry from the registry."""
        meta = meta or {}
        official_meta = meta.get("io.modelcontextprotocol.registry/official", {})

        repo = s.get("repository", {})
        repo_url = repo.get("url", "") if isinstance(repo, dict) else str(repo) if repo else ""

        return MCPServerInfo(
            id=s.get("name") or s.get("id") or "",
            name=s.get("title") or s.get("displayName") or s.get("name") or "",
            description=s.get("description") or "",
            repository=repo_url,
            homepage=s.get("websiteUrl") or s.get("homepage") or "",
            version=s.get("version") or "",
            license=s.get("license") or "",
            author=s.get("author") or s.get("vendor") or "",
            is_verified=official_meta.get("status") == "active",
            downloads=int(s.get("downloads") or s.get("installCount") or 0),
            created_at=official_meta.get("publishedAt") or s.get("createdAt") or "",
            updated_at=official_meta.get("updatedAt") or s.get("updatedAt") or "",
            categories=s.get("categories") or [],
            capabilities=s.get("capabilities") or [],
            install_config=s.get("packages") or s.get("remotes") or s.get("installations") or {},
        )


async def search_mcp_registry(query: str = "", limit: int = 50) -> list[MCPServerInfo]:
    """Convenience function to search the MCP Registry."""
    client = MCPRegistryClient()
    return await client.search(query, limit)
