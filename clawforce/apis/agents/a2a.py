"""Agent-to-agent (A2A) communication endpoints."""

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from clawforce.auth import get_user_or_agent
from clawforce.core.acp import RunStore
from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.store.agents import AgentStore
from clawforce.core.ws import ConnectionManager
from clawforce.deps import get_agent_store, get_run_store, get_runtime, get_ws_manager

from ._schemas import A2AMessageBody

logger = logging.getLogger(__name__)

router = APIRouter(tags=["a2a"])


async def _read_agents_md(runtime: AgentRuntimeBackend, agent_id: str) -> str:
    """Read the AGENTS.md profile file via agent API (WebSocket). Returns empty string if unavailable.

    Uses runtime.read_profile_file so admin can fetch capacity when agents run on different machines.
    """
    try:
        content = await runtime.read_profile_file(agent_id, "AGENTS.md")
        return content or ""
    except Exception:
        return ""


@router.get("/api/agents/me/peers")
async def list_peers(
    current: dict = Depends(get_user_or_agent),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """List all other agents available for A2A communication.

    Only callable by agents (via agent token). Returns all agents except the caller.
    Each peer includes a ``capacity`` field with the raw content of its AGENTS.md profile,
    giving the calling agent full context about the peer's role and responsibilities.
    Capacity is read via agent API (WebSocket), so it works when admin and agents are on different machines.
    """
    if current.get("type") != "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only agents can discover peers"
        )
    caller_agent_id = current.get("agent_id", "")

    peers = store.list_agents()
    result = []
    for a in peers:
        if a.id == caller_agent_id:
            continue
        runtime_status = await runtime.get_status(a.id)
        capacity = await _read_agents_md(runtime, a.id)
        result.append(
            {
                "id": a.id,
                "name": a.name,
                "description": a.description or "",
                "status": runtime_status.status,
                "capacity": capacity,
            }
        )
    return result


@router.post("/api/agents/{agent_id}/a2a-message")
async def send_a2a_message(
    agent_id: str,
    body: A2AMessageBody,
    current: dict = Depends(get_user_or_agent),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
    run_store: RunStore = Depends(get_run_store),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
):
    """Send a message from one agent to another (ACP-style, synchronous).

    Only callable by agents. Returns the target agent's reply in the same HTTP response.
    Blocks up to 120 seconds for the target agent to respond.
    """
    if current.get("type") != "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only agents can send A2A messages"
        )

    caller_agent_id = current.get("agent_id", "")
    if caller_agent_id == agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot send A2A message to yourself"
        )

    caller_agent = store.get_agent(caller_agent_id)
    target_agent = store.get_agent(agent_id) or store.get_agent_by_name(agent_id)

    if not caller_agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caller agent not found")
    if not target_agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target agent not found")

    agent_id = target_agent.id

    runtime_status = await runtime.get_status(agent_id)
    if runtime_status.status != "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Target agent is not running (status: {runtime_status.status})",
        )

    run_id = uuid.uuid4().hex
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    run_store.create(run_id, future)

    await ws_manager.send_to_agent(
        agent_id,
        {
            "type": "acp_run",
            "run_id": run_id,
            "text": body.message,
            "from_agent_id": caller_agent_id,
        },
    )

    try:
        reply = await asyncio.wait_for(future, timeout=120.0)
        return {"ok": True, "reply": reply}
    except asyncio.TimeoutError:
        run_store.reject(run_id, "timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Agent did not respond in time"
        )
    except Exception as e:
        logger.error(f"a2a-message error for run_id={run_id}: {e}", exc_info=True)
        run_store.remove(run_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"A2A message failed: {e}"
        )
