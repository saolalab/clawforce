"""MCPRegistry implementation using the official registry (registry.modelcontextprotocol.io)."""

from clawlib.mcpregistry.client import MCPRegistryClient


def _build_install_config(raw: dict | list) -> dict:
    """Build install config from official registry packages/remotes for InstallMcpModal."""
    items = raw if isinstance(raw, list) else [raw] if raw else []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "streamable-http" and item.get("url"):
            return {"url": str(item["url"])}
        # packages use registryType (npm) or type (npm)
        reg_type = item.get("registryType") or item.get("type")
        identifier = item.get("identifier")
        if reg_type == "npm" and identifier:
            return {"command": "npx", "args": ["-y", str(identifier)]}
        if reg_type == "pypi" and identifier:
            return {"command": "uvx", "args": [str(identifier)]}
    return {}


def _parse_required_env(raw: dict | list) -> list[str]:
    """Extract required env var names from remotes headers or packages environmentVariables."""
    items = raw if isinstance(raw, list) else [raw] if raw else []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for h in item.get("headers") or []:
            if isinstance(h, dict) and h.get("isRequired") and h.get("name"):
                name = str(h["name"])
                if name and name not in result:
                    result.append(name)
        for ev in item.get("environmentVariables") or []:
            if isinstance(ev, dict) and ev.get("isRequired") and ev.get("name"):
                name = str(ev["name"])
                if name and name not in result:
                    result.append(name)
    return result


def _server_to_dict(info) -> dict:
    """Convert MCPServerInfo to MCPRegistryServer dict shape."""
    raw_cfg = getattr(info, "install_config", None) or {}
    install_config = _build_install_config(raw_cfg)
    required_env = _parse_required_env(raw_cfg) if isinstance(raw_cfg, list) else []

    return {
        "id": info.id,
        "slug": info.id,
        "name": info.name,
        "description": info.description or "",
        "repository": info.repository or "",
        "homepage": info.homepage or "",
        "version": info.version or "",
        "license": info.license or "",
        "author": info.author or "",
        "verified": info.is_verified,
        "is_verified": info.is_verified,
        "downloads": info.downloads,
        "created_at": info.created_at or "",
        "updated_at": info.updated_at or "",
        "categories": info.categories or [],
        "capabilities": info.capabilities or [],
        "install_config": install_config,
        "required_env": required_env,
    }


class OfficialMCPRegistry:
    """MCPRegistry implementation using registry.modelcontextprotocol.io."""

    def __init__(self) -> None:
        self._client = MCPRegistryClient()

    async def search_mcp_servers(self, query: str, limit: int) -> list[dict]:
        """Search the official MCP registry."""
        servers = await self._client.search(query.strip(), limit=limit)
        return [_server_to_dict(s) for s in servers]

    async def get_mcp_server(self, slug: str) -> dict | None:
        """Get a single server from the official MCP registry."""
        server = await self._client.get_server(slug)
        if server is None:
            return None
        return _server_to_dict(server)
