"""WebSocket connection manager for agent control plane.

Supports fire-and-forget sends (messages, heartbeats) and request/response
with correlation IDs (config, workspace, skills, health).
"""

import asyncio
import uuid

from fastapi import WebSocket

_DEFAULT_TIMEOUT = 15.0


class ConnectionManager:
    """Track connected agents by agent_id and support request/response over WS."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._pending: dict[str, asyncio.Future] = {}

    def register(self, agent_id: str, ws: WebSocket) -> None:
        self._connections[agent_id] = ws

    def disconnect(self, agent_id: str) -> None:
        self._connections.pop(agent_id, None)

    def is_connected(self, agent_id: str) -> bool:
        return agent_id in self._connections

    async def send_to_agent(self, agent_id: str, data: dict) -> bool:
        """Fire-and-forget send to an agent. Returns True if sent."""
        ws = self._connections.get(agent_id)
        if ws is None:
            return False
        try:
            await ws.send_json(data)
            return True
        except Exception:
            return False

    async def request(
        self,
        agent_id: str,
        payload: dict,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> dict | None:
        """Send a request to an agent and wait for a correlated response.

        Returns the response dict, or None if the agent is disconnected or
        the request times out.
        """
        ws = self._connections.get(agent_id)
        if ws is None:
            return None
        request_id = uuid.uuid4().hex[:12]
        payload["request_id"] = request_id
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[request_id] = future
        try:
            await ws.send_json(payload)
            return await asyncio.wait_for(future, timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError):
            return None
        except Exception:
            return None
        finally:
            self._pending.pop(request_id, None)

    def resolve_response(self, request_id: str, data: dict) -> bool:
        """Resolve a pending request future with the given data.

        Called from the WebSocket hub when a ``response`` message arrives.
        Returns True if the request_id matched a pending request.
        """
        future = self._pending.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(data)
        return True
