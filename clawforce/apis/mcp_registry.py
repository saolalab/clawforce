"""API endpoints for the MCP server registry (registry.modelcontextprotocol.io by default)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from clawforce.apis.agents.crud import require_agent_access
from clawforce.auth import get_current_user
from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.runtimes._worker_runtime import WorkerRuntimeBase
from clawforce.core.store.agents import AgentStore
from clawforce.deps import get_agent_store, get_mcp_registry, get_runtime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mcp-registry"])


@router.get("/api/mcp-registry/search")
async def search_mcp_registry(
    q: str = "",
    limit: int = 50,
    _: dict = Depends(get_current_user),
    registry=Depends(get_mcp_registry),
):
    """Search the MCP server registry (official registry by default)."""
    try:
        servers = await registry.search_mcp_servers(q.strip(), limit=min(limit, 100))
    except Exception as e:
        logger.exception("MCP Registry search failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"MCP Registry error: {e!s}"
        )
    return servers


@router.get("/api/mcp-registry/servers/{server_id:path}")
async def get_mcp_server(
    server_id: str,
    _: dict = Depends(get_current_user),
    registry=Depends(get_mcp_registry),
):
    """Get details for a specific MCP server from the registry."""
    try:
        server = await registry.get_mcp_server(server_id)
    except Exception as e:
        logger.exception("MCP Registry get_server failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"MCP Registry error: {e!s}"
        )

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found in MCP Registry"
        )

    return server


class MCPInstallRequest(BaseModel):
    """Request to install an MCP server to an agent."""

    server_id: str
    server_name: str
    command: str = ""
    args: list[str] = []
    env: dict[str, str] = {}
    url: str = ""


@router.get("/api/agents/{agent_id}/mcp-servers")
async def list_mcp_servers(
    agent_id: str,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Get list of installed MCP servers and their connection status for an agent.

    Returns server status including name, connection status, tool count, and any errors.
    """
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, agent)

    runtime_status = await runtime.get_status(agent_id)
    mcp_servers = runtime_status.mcp or {}

    return {
        "agent_id": agent_id,
        "agent_status": runtime_status.status,
        "servers": mcp_servers,
    }


@router.get("/api/agents/{agent_id}/mcp-servers/{server_key}/tools")
async def list_mcp_server_tools(
    agent_id: str,
    server_key: str,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Get list of tools provided by a specific MCP server.

    The agent must be running to retrieve tools. Returns tool definitions including
    name, description, and parameters.
    """
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, agent)

    runtime_status = await runtime.get_status(agent_id)
    if runtime_status.status != "running":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent is not running (status: {runtime_status.status}). Start the agent first.",
        )

    mcp_servers = runtime_status.mcp or {}
    if server_key not in mcp_servers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_key}' not found or not connected",
        )

    # Only WorkerRuntimeBase supports WebSocket-based tool retrieval
    if not isinstance(runtime, WorkerRuntimeBase):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tool retrieval not supported for this runtime backend",
        )

    try:
        tools_defs = await runtime._ws_request(
            agent_id, "get_mcp_tools", server_key=server_key, timeout=10.0
        )
        if tools_defs and tools_defs.get("ok"):
            return {
                "agent_id": agent_id,
                "server_key": server_key,
                "tools": tools_defs.get("data", {}).get("tools", []),
            }
        return {
            "agent_id": agent_id,
            "server_key": server_key,
            "tools": [],
            "error": tools_defs.get("error", "Failed to fetch tools")
            if tools_defs
            else "Unknown error",
        }
    except Exception as e:
        logger.exception(f"Failed to get MCP tools for server {server_key}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to get MCP tools: {str(e)}",
        )


@router.post("/api/agents/{agent_id}/mcp-servers/install")
async def install_mcp_server(
    agent_id: str,
    body: MCPInstallRequest,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Install an MCP server to an agent's config.

    The server config is added to tools.mcp_servers. The agent needs to be
    restarted for the changes to take effect.
    """
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    runtime_status = await runtime.get_status(agent_id)
    if runtime_status.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent is not running (status: {runtime_status.status}). Start the agent first.",
        )

    server_key = body.server_name.replace("/", "_").replace(".", "_").replace("@", "")
    if not server_key:
        server_key = body.server_id.replace("/", "_").replace(".", "_").replace("@", "")

    mcp_config: dict = {}
    if body.url:
        mcp_config["url"] = body.url
        if body.env:
            mcp_config["env"] = body.env
    elif body.command:
        mcp_config["command"] = body.command
        mcp_config["args"] = body.args
        mcp_config["env"] = body.env
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'url' or 'command' must be provided",
        )

    config_update = {"tools": {"mcp_servers": {server_key: mcp_config}}}

    try:
        updated = await runtime.update_config(agent_id, config_update)
    except Exception as e:
        logger.exception("Failed to install MCP server")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to update config: {e!s}"
        )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Config update failed (agent may have stopped)",
        )

    return {
        "ok": True,
        "server_key": server_key,
        "message": f"MCP server '{server_key}' installed and connected.",
    }
