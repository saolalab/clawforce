"""MCP client: connects to MCP servers and wraps their tools as native clawbot tools.

Node.js-based servers get NODE_NO_WARNINGS=1 injected to suppress the
experimental JSON-import warning that causes Cursor-style hosts to report
a 502 install error.
"""

import asyncio
import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import httpx
from loguru import logger
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from clawbot.agent.tools.base import Tool, sanitize_tool_name
from clawbot.agent.tools.registry import ToolRegistry

_NODE_COMMANDS = frozenset({"node", "npx", "tsx"})


class MCPToolWrapper(Tool):
    """Wraps a single MCP server tool as a clawbot Tool."""

    def __init__(self, session, server_name: str, tool_def):
        self._session = session
        self._original_name = tool_def.name
        self._name = sanitize_tool_name(f"mcp_{server_name}_{tool_def.name}")
        self._description = tool_def.description or tool_def.name
        self._parameters = tool_def.inputSchema or {"type": "object", "properties": {}}

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, **kwargs: Any) -> str:
        result = await self._session.call_tool(self._original_name, arguments=kwargs)
        parts = []
        for block in result.content:
            if isinstance(block, types.TextContent):
                parts.append(block.text)
            else:
                parts.append(str(block))
        return "\n".join(parts) or "(no output)"


def _is_node_command(command: str) -> bool:
    basename = Path(command).name
    return basename in _NODE_COMMANDS


def _build_mcp_env(cfg_env: dict[str, str] | None, command: str) -> dict[str, str] | None:
    """Build environment for an MCP server process.

    Inherits parent env, merges config-specified overrides, and auto-adds
    NODE_NO_WARNINGS=1 for Node.js commands to suppress the experimental
    JSON-import warning that breaks Cursor/host install flows.
    """
    is_node = _is_node_command(command)

    if not cfg_env and not is_node:
        return None

    env = os.environ.copy()
    if cfg_env:
        env.update(cfg_env)
    if is_node:
        env.setdefault("NODE_NO_WARNINGS", "1")
    return env


def _build_stdio_params(cfg: Any) -> StdioServerParameters:
    """Build StdioServerParameters for an MCP stdio server."""
    env = _build_mcp_env(cfg.env, cfg.command)
    return StdioServerParameters(command=cfg.command, args=cfg.args, env=env)


class MCPServerStatus:
    """Runtime connection status of a single MCP server."""

    __slots__ = ("name", "status", "tools_count", "error", "needs_auth", "auth_url")

    def __init__(
        self,
        name: str,
        status: str,
        tools_count: int = 0,
        error: str = "",
        needs_auth: bool = False,
        auth_url: str = "",
    ):
        self.name = name
        self.status = status
        self.tools_count = tools_count
        self.error = error
        self.needs_auth = needs_auth
        # OAuth 2.1: resource_metadata URL from WWW-Authenticate header on 401.
        # When set, the UI should open this URL to initiate the OAuth flow
        # instead of asking for manual key/value credentials.
        self.auth_url = auth_url

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name, "status": self.status, "tools": self.tools_count}
        if self.error:
            d["error"] = self.error
        if self.needs_auth:
            d["needs_auth"] = True
        if self.auth_url:
            d["auth_url"] = self.auth_url
        return d


def _parse_www_authenticate_resource_metadata(header: str) -> str:
    """Extract resource_metadata URL from a WWW-Authenticate: Bearer header.

    Per MCP spec (RFC 9728): servers MUST include resource_metadata in the
    WWW-Authenticate header on 401 so clients can discover the OAuth 2.1
    authorization server.

    Example header value:
      Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"
    """
    import re

    m = re.search(r'resource_metadata=["\']?([^\s"\'>,]+)', header, re.IGNORECASE)
    return m.group(1) if m else ""


def _classify_mcp_error(e: BaseException, cfg: Any) -> tuple[str, bool, str]:
    """Return (error_message, needs_auth, auth_url) for an MCP connection failure.

    needs_auth=True  → server needs credentials not yet provided.
    auth_url non-empty → server advertises OAuth 2.1 via WWW-Authenticate;
                         the UI should open this URL instead of showing a form.
    """
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        body = e.response.text[:200].strip()
        needs_auth = code in (401, 403)
        auth_url = ""
        if code == 401:
            www_auth = e.response.headers.get("WWW-Authenticate", "")
            auth_url = _parse_www_authenticate_resource_metadata(www_auth)
        hints = {
            401: "unauthorized — check API key or token",
            403: "forbidden — check API key or token",
            404: "endpoint not found — verify the URL",
        }
        hint = hints.get(
            code,
            "server error — the remote MCP server may be down"
            if code >= 500
            else "unexpected response",
        )
        msg = f"HTTP {code}: {hint}" + (f" ({body})" if body else "")
        return msg, needs_auth, auth_url

    if isinstance(e, httpx.ConnectError):
        return f"connection refused or DNS failure: {e}", False, ""
    if isinstance(e, httpx.TimeoutException):
        return f"connection timed out: {e}", False, ""
    if isinstance(e, httpx.RemoteProtocolError):
        return f"remote protocol error (server may not speak MCP): {e}", False, ""

    err_msg = str(e) or repr(e)
    lower = err_msg.lower()

    # stdio: process exited immediately → almost always missing env var / API key
    if cfg.command and ("connection closed" in lower or "eof" in lower or "broken pipe" in lower):
        return (
            f"process exited immediately — check required env vars (API keys): {err_msg}",
            True,
            "",
        )

    # HTTP streamable: session terminated / cancelled during handshake
    if cfg.url and (
        "session terminated" in lower or "cancelled" in lower or "cancel scope" in lower
    ):
        return (
            f"session terminated during handshake — server may require auth headers: {err_msg}",
            True,
            "",
        )

    return err_msg, False, ""


async def connect_mcp_servers(
    mcp_servers: dict,
    registry: ToolRegistry,
    stack: AsyncExitStack,
) -> dict[str, MCPServerStatus]:
    """Connect to configured MCP servers and register their tools.

    Returns a dict of server name -> MCPServerStatus so callers can inspect
    which servers succeeded, failed, or were skipped.  Failures are logged
    but never propagate — no single MCP server can take down the agent loop.
    """
    statuses: dict[str, MCPServerStatus] = {}
    current_task = asyncio.current_task()

    for name, cfg in mcp_servers.items():
        cancel_count_before = current_task.cancelling() if current_task else 0
        try:
            if cfg.command:
                params = _build_stdio_params(cfg)
                read, write = await stack.enter_async_context(stdio_client(params))
            elif cfg.url:
                http_client = httpx.AsyncClient(headers=cfg.headers) if cfg.headers else None
                read, write, _ = await stack.enter_async_context(
                    streamable_http_client(cfg.url, http_client=http_client)
                )
            else:
                logger.warning("MCP server '{}': no command or url configured, skipping", name)
                statuses[name] = MCPServerStatus(name, "skipped", error="no command or url")
                continue

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            tools = await session.list_tools()
            allowed: set[str] | None = set(cfg.enabled_tools) if cfg.enabled_tools else None

            registered = 0
            for tool_def in tools.tools:
                if allowed is not None and tool_def.name not in allowed:
                    logger.debug("MCP: skipping tool '{}' (not in enabled_tools)", tool_def.name)
                    continue
                wrapper = MCPToolWrapper(session, name, tool_def)
                registry.register(wrapper)
                registered += 1
                logger.debug("MCP: registered tool '{}' from server '{}'", wrapper.name, name)

            statuses[name] = MCPServerStatus(name, "connected", tools_count=registered)
            logger.info("MCP server '{}': connected, {} tools registered", name, registered)
        except BaseException as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            # anyio cancel-scopes raise CancelledError which can increment
            # the asyncio task's cancelling counter multiple times (nested
            # scopes).  Drain all leaked increments so the agent loop
            # isn't killed by a single MCP server failure.
            if current_task and isinstance(e, asyncio.CancelledError):
                while current_task.cancelling() > cancel_count_before:
                    current_task.uncancel()
            err_msg, needs_auth, auth_url = _classify_mcp_error(e, cfg)
            statuses[name] = MCPServerStatus(
                name, "failed", error=err_msg, needs_auth=needs_auth, auth_url=auth_url
            )
            cmd_or_url = getattr(cfg, "command", "") or getattr(cfg, "url", "") or "?"
            logger.error(
                "MCP server '{}': failed to connect: {} (command={})",
                name,
                err_msg,
                cmd_or_url,
            )

    return statuses
