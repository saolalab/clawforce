"""McpManager: MCP server connection and lifecycle management."""

import asyncio
from contextlib import AsyncExitStack

from loguru import logger

from clawbot.agent.tools.mcp import MCPServerStatus, connect_mcp_servers
from clawbot.agent.tools.registry import ToolRegistry
from clawlib.config.schema import MCPServerConfig


class McpManager:
    """Manages MCP server connections. Owns all MCP state and dependencies."""

    def __init__(
        self,
        mcp_registry: ToolRegistry,
        initial_servers: dict[str, MCPServerConfig] | None = None,
    ) -> None:
        self.mcp = mcp_registry
        self._servers: dict[str, MCPServerConfig] = dict(initial_servers or {})
        self._stack: AsyncExitStack | None = None
        self._connected = False
        self._connect_task: asyncio.Task | None = None
        self._status: dict[str, MCPServerStatus] = {}

    async def register_server(self, key: str, config: dict) -> MCPServerStatus:
        """Register a new MCP server at runtime (called after install via config).

        Connects to the server, registers its tools, and returns the status.
        """
        if key in self._servers:
            return MCPServerStatus(key, "skipped", error="already registered")

        cfg = MCPServerConfig.model_validate(config)
        if not cfg.command and not cfg.url:
            return MCPServerStatus(key, "failed", error="no command or url")

        if self._stack is None:
            self._stack = AsyncExitStack()
            await self._stack.__aenter__()

        status = await connect_mcp_servers({key: cfg}, self.mcp, self._stack)
        server_status = status.get(key, MCPServerStatus(key, "failed", error="unknown"))

        if server_status.status == "connected":
            self._servers[key] = cfg
            self._status[key] = server_status
            logger.info("Registered MCP server at runtime: {}", key)
        else:
            logger.warning("Failed to register MCP server {}: {}", key, server_status.error)

        return server_status

    def unregister_server(self, key: str) -> None:
        """Unregister an MCP server at runtime.

        Removes its tools from the registry. The server process keeps running
        until shutdown (close); it cannot be stopped per-server.
        """
        prefix = f"mcp_{key}_"
        to_remove = [name for name in self.mcp.tool_names if name.startswith(prefix)]
        for name in to_remove:
            self.mcp.unregister(name)
        self._servers.pop(key, None)
        self._status.pop(key, None)
        logger.info("Unregistered MCP server: {} ({} tools removed)", key, len(to_remove))

    def connect(self) -> None:
        """Start MCP connection in background. Returns immediately; agent loop can run without waiting."""
        if self._connected or not self._servers:
            return
        self._connected = True
        self._connect_task = asyncio.create_task(self._connect())

    async def await_connected(self, timeout: float = 15.0) -> None:
        """Wait for the background MCP connection task to finish (up to `timeout` seconds).

        Safe to call even if connect() was never called or already finished.
        Used at agent startup so the first message sees all MCP tools in the system prompt.
        """
        if self._connect_task is None or self._connect_task.done():
            return
        try:
            await asyncio.wait_for(asyncio.shield(self._connect_task), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("MCP connection did not finish within {}s; continuing anyway", timeout)

    async def _connect(self) -> None:
        """Connect to configured MCP servers (one-time). Runs in background task."""
        try:
            self._stack = AsyncExitStack()
            await self._stack.__aenter__()

            async def _isolated() -> dict[str, MCPServerStatus]:
                return await connect_mcp_servers(
                    self._servers,
                    self.mcp,
                    self._stack,
                )

            child = asyncio.create_task(_isolated())
            try:
                self._status = await child
                logger.info("MCP servers connected ({} total)", len(self._status))
            except asyncio.CancelledError:
                if (task := asyncio.current_task()) and task.cancelling() > 0:
                    raise
                self._status = {
                    n: MCPServerStatus(n, "failed", error="connection cancelled")
                    for n in self._servers
                }
                logger.warning("MCP connection task cancelled")
            except Exception as e:
                self._status = {}
                logger.error("MCP connection task failed: {}", e)
        finally:
            self._connect_task = None

    async def close(self) -> None:
        """Close MCP connections."""
        if self._connect_task and not self._connect_task.done():
            self._connect_task.cancel()
            try:
                await self._connect_task
            except asyncio.CancelledError:
                pass
        if self._stack:
            try:
                await self._stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass  # MCP SDK cancel scope cleanup is noisy but harmless
            self._stack = None

    @property
    def status(self) -> dict[str, MCPServerStatus]:
        """Per-server MCP connection status (populated after first connect)."""
        return self._status

    @property
    def servers(self) -> dict[str, MCPServerConfig]:
        """Currently registered MCP server configs."""
        return self._servers
