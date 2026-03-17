"""MCP Registry client and implementation for the official Model Context Protocol registry.

.. deprecated::
   Use :mod:`clawlib.registry` and :func:`get_mcp_registry` instead.
   Uses official MCP registry (registry.modelcontextprotocol.io).
"""

from clawlib.mcpregistry.client import (
    MCPRegistryClient,
    search_mcp_registry,
)
from clawlib.mcpregistry.models import MCPServerInfo
from clawlib.mcpregistry.official_mcp import OfficialMCPRegistry

__all__ = [
    "MCPRegistryClient",
    "MCPServerInfo",
    "OfficialMCPRegistry",
    "search_mcp_registry",
]
