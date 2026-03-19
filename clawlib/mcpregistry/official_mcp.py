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


_FILE_HINTS = frozenset(
    {
        "credentials_file",
        "credentials_json",
        "oauth_credentials",
        "google_credentials",
        "client_secret_file",
    }
)


def _infer_widget_for_field(name: str, entry: dict) -> str:
    """Infer the widget type from field name and registry metadata.

    Returns "file" when the name or format hints at a JSON file upload
    (e.g. Google OAuth credentials.json), otherwise empty string (default text input).
    """
    lower = name.lower()
    fmt = str(entry.get("format") or entry.get("type") or "").lower()
    if fmt in ("file", "json_file", "oauth_file") or lower in _FILE_HINTS:
        return "file"
    if "file" in lower and ("json" in lower or "credential" in lower or "secret" in lower):
        return "file"
    return ""


def _parse_config_schema(raw: dict | list) -> list[dict]:
    """Extract config schema from remotes headers or packages environmentVariables.

    Returns a list of dicts with JSON Schema properties: name, title, description,
    type, format, x-widget, default, enum, required. The UI renders from this schema.
    """
    items = raw if isinstance(raw, list) else [raw] if raw else []
    seen: set[str] = set()
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for entry in [*item.get("headers", []), *item.get("environmentVariables", [])]:
            if not isinstance(entry, dict) or not entry.get("isRequired"):
                continue
            name = str(entry.get("name") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            widget = _infer_widget_for_field(name, entry)
            result.append(
                {
                    "name": name,
                    "title": str(
                        entry.get("label") or entry.get("title") or entry.get("name") or name
                    ),
                    "description": str(entry.get("description") or ""),
                    "type": "string",
                    "format": "password" if not widget else "",
                    "x-widget": widget,
                    "required": True,
                }
            )
    return result


def _server_to_dict(info) -> dict:
    """Convert MCPServerInfo to MCPRegistryServer dict shape."""
    raw_cfg = getattr(info, "install_config", None) or {}
    install_config = _build_install_config(raw_cfg)
    config_schema = _parse_config_schema(raw_cfg) if isinstance(raw_cfg, list) else []

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
        "config_schema": config_schema,
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
