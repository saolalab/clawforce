"""ACP (Agent Communication Protocol) integration.

RunStore: correlates run_id → asyncio.Future for synchronous A2A message handling.
When Alice calls Bob, we create a Future and wait for Bob's WS response to resolve it.
"""

import asyncio


class RunStore:
    """Correlates run_id → asyncio.Future for the pending HTTP response.

    When Alice sends a message to Bob via POST /api/agents/{id}/a2a-message,
    we create a Future and hold the HTTP connection open. When Bob's response
    arrives via the WebSocket as an acp_run_result message, we resolve the Future
    and return the reply in the HTTP response.
    """

    def __init__(self) -> None:
        self._futures: dict[str, asyncio.Future] = {}

    def create(self, run_id: str, future: asyncio.Future) -> None:
        """Register a Future for a run_id."""
        self._futures[run_id] = future

    def resolve(self, run_id: str, content: str) -> None:
        """Resolve the pending Future with the response content."""
        fut = self._futures.pop(run_id, None)
        if fut and not fut.done():
            fut.set_result(content)

    def reject(self, run_id: str, error: str) -> None:
        """Reject the pending Future with an error."""
        fut = self._futures.pop(run_id, None)
        if fut and not fut.done():
            fut.set_exception(RuntimeError(error))

    def remove(self, run_id: str) -> None:
        """Remove a run_id from the store (cleanup on error)."""
        self._futures.pop(run_id, None)
