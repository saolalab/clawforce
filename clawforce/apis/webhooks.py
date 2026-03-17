"""Webhook endpoints for external services (Teams, etc.)."""

import logging

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from clawforce.core.store.agents import AgentStore
from clawforce.core.ws import ConnectionManager
from clawforce.deps import get_agent_store, get_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


@router.post("/api/webhooks/teams/{agent_id}")
async def teams_webhook(
    agent_id: str,
    request: Request,
    store: AgentStore = Depends(get_agent_store),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
):
    """Receive Bot Framework Activity from Microsoft Teams. Forwards to agent via control plane."""
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("Teams webhook: invalid JSON: %s", e)
        return JSONResponse(
            {"status": "error", "message": "Invalid JSON"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    activity_type = body.get("type", "")
    if activity_type != "message":
        return {"status": "ok"}

    text = body.get("text", "").strip()
    if not text:
        return {"status": "ok"}

    conversation = body.get("conversation") or {}
    conversation_id = conversation.get("id", "")
    service_url = body.get("serviceUrl", "")
    from_user = body.get("from") or {}
    user_id = from_user.get("id", "")

    agent = store.get_agent(agent_id)
    if not agent or not agent.enabled:
        logger.warning("Teams webhook: agent %s not found or disabled", agent_id)
        return JSONResponse(
            {"status": "error", "message": "Agent not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if not ws_manager.is_connected(agent_id):
        logger.warning("Teams webhook: agent %s not connected", agent_id)
        return JSONResponse(
            {"status": "error", "message": "Agent not connected"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    teams_context = {
        "service_url": service_url,
        "conversation_id": conversation_id,
    }

    ok = await ws_manager.send_to_agent(
        agent_id,
        {
            "type": "teams_message",
            "text": text,
            "channel": "teams",
            "chat_id": conversation_id,
            "session_key": f"teams:{conversation_id}",
            "teams_context": teams_context,
            "sender_id": user_id,
        },
    )
    if not ok:
        return JSONResponse(
            {"status": "error", "message": "Failed to forward"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return {"status": "ok"}
