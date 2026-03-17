"""AdminClient: WebSocket transport between worker and admin control plane.

Protocol: Agent sends register -> Admin responds registered -> connection established.
State: DISCONNECTED -> CONNECTED (after register) -> RUNNING (loops). On disconnect -> DISCONNECTED.
Reconnection uses exponential backoff from connection_config.
"""

import asyncio
import json
import logging
import uuid
from pathlib import Path

import websockets
from websockets.connection import State

from clawbot.core.connection_config import (
    HEARTBEAT_INTERVAL_MIN_S,
    RECONNECT_BACKOFF_FACTOR,
    RECONNECT_DELAY_INITIAL_S,
    RECONNECT_DELAY_MAX_S,
    REGISTER_TIMEOUT_S,
    REQUEST_TIMEOUT_S,
)
from clawbot.worker.context import WorkerContext
from clawbot.worker.handlers import dispatch
from clawlib.activity import ActivityEvent
from clawlib.bus import InboundMessage

logger = logging.getLogger(__name__)


def _read_activity_jsonl(logs_path: Path) -> list[ActivityEvent]:
    """Read activity events from JSONL files on disk (oldest-first order).

    Reads rotated files: activity.2.jsonl, activity.1.jsonl, activity.jsonl.
    Assigns event_id if missing (for events written before event_id was added).
    Returns list sorted by timestamp.
    """
    events: list[ActivityEvent] = []
    # Oldest first: activity.2.jsonl, activity.1.jsonl, activity.jsonl
    file_order = ["activity.2.jsonl", "activity.1.jsonl", "activity.jsonl"]
    for filename in file_order:
        path = logs_path / filename
        if not path.exists():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ev = ActivityEvent(
                    agent_id=data.get("agent_id", ""),
                    event_type=data.get("event_type", ""),
                    channel=data.get("channel", ""),
                    content=data.get("content", ""),
                    plan_id=data.get("plan_id", ""),
                    timestamp=data.get("timestamp", ""),
                    tool_name=data.get("tool_name"),
                    result_status=data.get("result_status"),
                    duration_ms=data.get("duration_ms"),
                    event_id=data.get("event_id"),
                )
                if ev.event_id is None:
                    ev.event_id = uuid.uuid4().hex
                events.append(ev)
        except OSError:
            continue
    events.sort(key=lambda e: e.timestamp or "")
    return events


class AdminConnectionError(Exception):
    """Raised when connection or registration fails."""


class AdminClient:
    """WebSocket client connecting a worker to the admin control plane.

    Bootstrap: connect() -> get_config() -> set_context(ctx) -> run().
    """

    def __init__(
        self,
        admin_url: str,
        agent_token: str,
        agent_id: str,
        heartbeat_interval: int = 30,
        ws_path: str = "/api/control/ws",
    ) -> None:
        base = (
            admin_url.strip().rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
        )
        self._ws_url = f"{base}{ws_path}"
        self._agent_id = agent_id
        self._agent_token = agent_token
        self._heartbeat_interval = max(HEARTBEAT_INTERVAL_MIN_S, heartbeat_interval)
        self._ctx: WorkerContext | None = None
        self._ws: websockets.WebSocketClientProtocol | None = None

    def is_connected(self) -> bool:
        """True if WebSocket is open and registered."""
        return self._ws is not None and self._ws.state == State.OPEN

    # -- Bootstrap: connect and fetch ------------------------------------------

    async def connect(self) -> None:
        """Open WebSocket, send register, wait for registered. Raises on timeout or rejection."""
        self._ws = await websockets.connect(self._ws_url)
        await self._ws.send(
            json.dumps(
                {
                    "type": "register",
                    "agent_id": self._agent_id,
                    "token": self._agent_token,
                }
            )
        )
        raw = await asyncio.wait_for(self._ws.recv(), timeout=REGISTER_TIMEOUT_S)
        data = json.loads(raw) if isinstance(raw, str) else raw
        if data.get("type") != "registered" or not data.get("ok"):
            raise AdminConnectionError(
                f"Expected {{type: registered, ok: true}}, got {data.get('type', '?')}"
            )

    async def request(self, action: str) -> dict:
        """Send a request to admin and wait for response. Used during BOOTSTRAPPING."""
        if not self._ws:
            raise AdminConnectionError("Not connected")
        request_id = uuid.uuid4().hex[:12]
        await self._ws.send(
            json.dumps(
                {
                    "type": "request",
                    "action": action,
                    "request_id": request_id,
                }
            )
        )
        try:
            while True:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=REQUEST_TIMEOUT_S)
                data = json.loads(raw) if isinstance(raw, str) else raw
                if data.get("type") == "response" and data.get("request_id") == request_id:
                    if not data.get("ok"):
                        raise AdminConnectionError(data.get("error", "Request failed"))
                    return data
        except asyncio.TimeoutError:
            raise AdminConnectionError(f"Request {action} timed out")

    async def get_config(self) -> dict:
        """Fetch full config from admin over WS (BOOTSTRAPPING). Includes control_plane, providers, channels, plain config."""
        resp = await self.request("get_config")
        return resp.get("data") or {}

    def set_context(self, ctx: WorkerContext) -> None:
        """Attach WorkerContext; enables full dispatch (READY state)."""
        self._ctx = ctx

    # -- Run loop (READY state) ------------------------------------------------

    async def run(self) -> None:
        """Run receive, heartbeat, and activity loops. Call after set_context(ctx). Returns when disconnected."""
        if not self._ctx or not self._ws:
            return
        await self._run_loops(self._ws)

    async def stop(self) -> None:
        """Disconnect cleanly."""
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def run_with_reconnect(self, stop: asyncio.Event) -> None:
        """Connect (or reuse existing), run loops, reconnect with backoff on disconnect. Stops when stop is set."""
        delay_s = RECONNECT_DELAY_INITIAL_S
        while not stop.is_set():
            try:
                if not self.is_connected():
                    await self.connect()
                    await self.report_status({"status": "running"})
                    logger.info("Admin WebSocket connected (workspace/config available)")
                await self.run()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.warning(
                    "Admin WebSocket disconnected: %s; reconnecting in %.1fs...", e, delay_s
                )
            self._ws = None
            if not stop.is_set():
                await asyncio.sleep(delay_s)
                delay_s = min(delay_s * RECONNECT_BACKOFF_FACTOR, RECONNECT_DELAY_MAX_S)

    async def report_status(self, status: dict) -> None:
        """Send status to admin (e.g. bootstrapping, running)."""
        if not self._ws:
            return
        await self._ws.send(json.dumps({"type": "status", "status": status}))

    async def push_activity(
        self, events: list[ActivityEvent], ws: websockets.WebSocketClientProtocol | None = None
    ) -> None:
        """Push activity events to admin."""
        w = ws or self._ws
        if not w or not events:
            return
        batch = []
        for e in events:
            entry: dict = {
                "agent_id": e.agent_id,
                "event_type": e.event_type,
                "channel": e.channel,
                "content": e.content,
                "timestamp": e.timestamp,
                "plan_id": e.plan_id,
            }
            if e.tool_name is not None:
                entry["tool_name"] = e.tool_name
            if e.result_status is not None:
                entry["result_status"] = e.result_status
            if e.duration_ms is not None:
                entry["duration_ms"] = e.duration_ms
            if e.event_id is not None:
                entry["event_id"] = e.event_id
            batch.append(entry)
        await w.send(json.dumps({"type": "activity", "events": batch}))

    async def _run_loops(self, ws: websockets.WebSocketClientProtocol) -> None:
        tasks = [
            asyncio.create_task(self._receive_loop(ws)),
            asyncio.create_task(self._heartbeat_loop(ws)),
            asyncio.create_task(self._activity_push_loop(ws)),
            asyncio.create_task(self._acp_forward_loop(ws)),
        ]
        try:
            _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()
            raise

    async def _receive_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        try:
            async for raw in ws:
                data = json.loads(raw) if isinstance(raw, str) else raw
                msg_type = data.get("type")
                if msg_type == "message":
                    if not self._ctx:
                        continue
                    text = data.get("text", "")
                    channel = data.get("channel", "cli")
                    chat_id = data.get("chat_id", "direct")
                    session_key = data.get("session_key", "cli:direct")
                    approval_msg = InboundMessage(
                        channel=channel,
                        sender_id="user",
                        chat_id=chat_id,
                        content=text,
                    )
                    if self._ctx.agent_loop.try_resolve_approval(approval_msg):
                        continue
                    await self._ctx.agent_loop.process_direct(
                        text,
                        session_key=session_key,
                        channel=channel,
                        chat_id=chat_id,
                    )
                elif msg_type == "teams_message":
                    if not self._ctx:
                        continue
                    text = data.get("text", "")
                    channel = data.get("channel", "teams")
                    chat_id = data.get("chat_id", "")
                    session_key = data.get("session_key", f"teams:{chat_id}")
                    teams_context = data.get("teams_context") or {}
                    teams_ch = self._ctx.channels.get_channel("teams")
                    if teams_ch and hasattr(teams_ch, "store_context") and teams_context:
                        teams_ch.store_context(chat_id, teams_context)
                    await self._ctx.agent_loop.process_direct(
                        text,
                        session_key=session_key,
                        channel=channel,
                        chat_id=chat_id,
                    )
                elif msg_type == "acp_run":
                    if not self._ctx:
                        continue
                    run_id = data.get("run_id", "")
                    text = data.get("text", "")
                    logger.info(f"ACP run received: run_id={run_id}")
                    asyncio.create_task(self._handle_acp_run(run_id, text))
                elif msg_type == "request" and self._ctx:
                    asyncio.create_task(self._handle_request(ws, data))
        except (asyncio.CancelledError, websockets.exceptions.ConnectionClosed):
            pass

    async def _handle_acp_run(self, run_id: str, text: str) -> None:
        if not self._ctx:
            return
        logger.info(f"ACP run processing: run_id={run_id}")
        try:
            reply = await self._ctx.agent_loop.process_direct(
                text,
                session_key=f"acp:{run_id}",
                channel="acp",
                chat_id=f"acp:{run_id}",
            )
            logger.info(f"ACP run complete: run_id={run_id}, reply_len={len(reply)}")
        except Exception as e:
            logger.error(f"ACP run error: run_id={run_id}, error={e}")

    async def _handle_request(self, ws: websockets.WebSocketClientProtocol, data: dict) -> None:
        if not self._ctx:
            return
        request_id = data.get("request_id", "")
        action = data.get("action", "")
        try:
            result = await dispatch(
                action,
                data,
                agent_loop=self._ctx.agent_loop,
                activity_log=self._ctx.activity_log,
                file_service=self._ctx.file_service,
                engine=self._ctx.engine,
                ctx=self._ctx,
            )
            resp = {"type": "response", "request_id": request_id, "ok": True, **result}
        except Exception as e:
            resp = {"type": "response", "request_id": request_id, "ok": False, "error": str(e)}
        try:
            await ws.send(json.dumps(resp))
        except Exception:
            pass

    async def _acp_forward_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Forward ACP run results back to clawforce to resolve the pending HTTP Future."""
        if not self._ctx:
            return
        bus = self._ctx.agent_loop.bus
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(bus.consume_acp_outbound(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                run_id = msg.chat_id.split(":", 1)[1] if ":" in msg.chat_id else ""
                if not run_id:
                    continue
                await ws.send(
                    json.dumps(
                        {
                            "type": "acp_run_result",
                            "run_id": run_id,
                            "content": msg.content,
                        }
                    )
                )
        except (asyncio.CancelledError, websockets.exceptions.ConnectionClosed):
            pass

    async def _heartbeat_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                await ws.send(json.dumps({"type": "heartbeat"}))
        except (asyncio.CancelledError, websockets.exceptions.ConnectionClosed):
            pass

    async def _activity_push_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Push activity in real-time: JSONL replay (survives restarts), backlog, then live stream."""
        if not self._ctx:
            return
        try:
            # Replay JSONL from disk (survives restarts; INSERT OR IGNORE deduplicates)
            logs_path = getattr(self._ctx.activity_log, "_logs_path", None)
            if logs_path and logs_path.exists():
                jsonl_events = _read_activity_jsonl(logs_path)
                if jsonl_events:
                    await self.push_activity(jsonl_events, ws=ws)
            # In-memory backlog (may overlap; deduplication handles it)
            backlog = self._ctx.activity_log.recent(limit=500)
            if backlog:
                await self.push_activity(backlog, ws=ws)
            # Stream new events live
            async for event in self._ctx.activity_log.subscribe():
                await self.push_activity([event], ws=ws)
        except (asyncio.CancelledError, websockets.exceptions.ConnectionClosed):
            pass
