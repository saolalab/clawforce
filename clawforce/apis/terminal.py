"""WebSocket endpoint for admin terminal (exec into Docker container or local shell).

Uses runtime.supports_terminal() and runtime.get_terminal_target() so no runtime backend
is imported at module level. Bridge logic lives in clawforce.core.runtimes.docker
and clawforce.core.runtimes.local and is imported only when the corresponding
backend is used.
"""

import logging

from fastapi import APIRouter, Query, WebSocket

from clawforce.auth import decode_token
from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.stream_token import verify_stream_token

router = APIRouter(tags=["terminal"])
logger = logging.getLogger(__name__)


def _verify_token(token: str | None) -> dict:
    """Verify JWT or short-lived stream token. Prefers stream tokens for WS query params."""
    if not token:
        raise ValueError("Missing token")
    stream_claims = verify_stream_token(token)
    if stream_claims:
        return stream_claims
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise ValueError("Invalid token")
    return payload


@router.websocket("/api/agents/{agent_id}/terminal")
async def terminal_ws(
    websocket: WebSocket,
    agent_id: str,
    token: str | None = Query(None),
):
    await websocket.accept()
    try:
        _verify_token(token)
    except ValueError as e:
        await websocket.close(code=4001, reason=str(e))
        return

    runtime: AgentRuntimeBackend | None = getattr(websocket.app.state, "runtime", None)
    if not runtime:
        await websocket.send_json({"type": "error", "data": "Runtime not available"})
        await websocket.close()
        return

    if not runtime.supports_terminal():
        await websocket.send_json(
            {"type": "error", "data": "Terminal not supported for this runtime backend"}
        )
        await websocket.close()
        return

    target_info = runtime.get_terminal_target(agent_id)
    if target_info is None:
        await websocket.send_json({"type": "error", "data": "Agent not running"})
        await websocket.close()
        return

    kind, target = target_info
    try:
        if kind == "docker":
            from clawforce.core.runtimes.docker import bridge_docker_terminal

            await bridge_docker_terminal(websocket, target, agent_id)
        elif kind == "local":
            from clawforce.core.runtimes.local import bridge_local_terminal

            await bridge_local_terminal(websocket, agent_id, target)
        else:
            await websocket.send_json({"type": "error", "data": "Unknown terminal backend"})
    except Exception:
        logger.exception(f"Terminal bridge error for agent {agent_id}")
        try:
            await websocket.send_json({"type": "error", "data": "Bridge error"})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
