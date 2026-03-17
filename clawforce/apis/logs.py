"""SSE endpoints for live agent activity logs and subprocess log tailing."""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sse_starlette.sse import EventSourceResponse

from clawforce.auth import decode_token
from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.store.process_logs import ProcessLogStore
from clawforce.core.stream_token import verify_stream_token
from clawforce.deps import get_activity_events_store, get_process_log_store, get_runtime

logger = logging.getLogger(__name__)

# Activity stream
ACTIVITY_RECENT_LIMIT = 100
ACTIVITY_PING_INTERVAL = 20
ACTIVITY_DB_POLL_INTERVAL = 0.3  # poll DB for new events (reliable; subscribe can fail)

# Process log stream
PROCESS_LOG_TAIL_BACKLOG = 100
PROCESS_LOG_POLL_INTERVAL = 0.1  # shorter sleep when waiting for next line
PROCESS_LOG_PING_INTERVAL = 15
PROCESS_LOG_BLOCK_SIZE = 64 * 1024

router = APIRouter(tags=["logs"])

# Headers to disable proxy/CDN buffering for real-time SSE
SSE_HEADERS = {
    "X-Accel-Buffering": "no",  # nginx
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Connection": "keep-alive",
}


def _verify_token(request: Request) -> dict:
    """Verify JWT or short-lived stream token from Authorization header or ?token= param."""
    token = request.query_params.get("token") or (
        request.headers.get("Authorization") or ""
    ).replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    # Try short-lived stream token first (preferred for SSE/WS query params)
    stream_claims = verify_stream_token(token)
    if stream_claims:
        return stream_claims
    # Fall back to long-lived JWT
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


@router.get("/api/agents/{agent_id}/logs")
async def agent_logs(
    request: Request,
    agent_id: str,
    runtime: AgentRuntimeBackend = Depends(get_runtime),
    activity_store=Depends(get_activity_events_store),
):
    _verify_token(request)

    def _event_data_from_obj(event) -> dict:
        """Build SSE payload from event (ActivityEvent or DB row dict)."""
        ts = (
            event.get("timestamp", "")
            if isinstance(event, dict)
            else getattr(event, "timestamp", "")
        )
        payload: dict = {
            "timestamp": ts,
            "event_type": event.get("event_type", "")
            if isinstance(event, dict)
            else getattr(event, "event_type", ""),
            "channel": event.get("channel", "")
            if isinstance(event, dict)
            else getattr(event, "channel", ""),
            "content": event.get("content", "")
            if isinstance(event, dict)
            else getattr(event, "content", ""),
        }
        tool_name = (
            event.get("tool_name") if isinstance(event, dict) else getattr(event, "tool_name", None)
        )
        if tool_name is not None:
            payload["tool_name"] = tool_name
        result_status = (
            event.get("result_status")
            if isinstance(event, dict)
            else getattr(event, "result_status", None)
        )
        if result_status is not None:
            payload["result_status"] = result_status
        duration_ms = (
            event.get("duration_ms")
            if isinstance(event, dict)
            else getattr(event, "duration_ms", None)
        )
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        event_id = (
            event.get("event_id") if isinstance(event, dict) else getattr(event, "event_id", None)
        )
        if event_id is not None:
            payload["event_id"] = event_id
        return {"event": "message", "data": json.dumps(payload)}

    def _agent_connected() -> bool:
        ws_connected = getattr(runtime, "_is_ws_connected", None)
        return ws_connected(agent_id) if ws_connected else False

    async def _container_running() -> bool:
        """True if Docker runtime and agent container exists and is running."""
        check = getattr(runtime, "_is_container_running", None)
        if check:
            return await check(agent_id)
        return False

    async def event_stream():
        try:
            yield {"event": "ping", "data": ""}
            # Always yield recent from DB first (works across workers, provides audit trail)
            backlog = activity_store.get_recent(agent_id, limit=ACTIVITY_RECENT_LIMIT)
            for row in backlog:
                yield _event_data_from_obj(row)
            last_id = max((r["id"] for r in backlog), default=None)
            if not _agent_connected():
                container_up = await _container_running()
                if container_up:
                    logger.warning(
                        "[%s] Agent container running; waiting for WebSocket. "
                        "Check ADMIN_PUBLIC_URL and agent process logs if this persists.",
                        agent_id,
                    )
                else:
                    logger.info(
                        "[%s] Agent not connected. Activity will appear when the agent connects to the control plane.",
                        agent_id,
                    )
            # Always poll DB for new events (DB is source of truth)
            while True:
                await asyncio.sleep(ACTIVITY_DB_POLL_INTERVAL)
                new_rows = activity_store.get_recent(agent_id, limit=50, after_id=last_id)
                for row in new_rows:
                    yield _event_data_from_obj(row)
                    last_id = row["id"]
                yield {"event": "ping", "data": ""}
        except (asyncio.CancelledError, GeneratorExit):
            return

    return EventSourceResponse(
        event_stream(),
        ping=ACTIVITY_PING_INTERVAL,
        headers=SSE_HEADERS,
    )


def _resolve_worker_log(runtime: AgentRuntimeBackend, agent_id: str) -> Path | None:
    """Return worker log path from runtime.get_log_path(), or None if unavailable."""
    getter = getattr(runtime, "get_log_path", None)
    if getter:
        return getter(agent_id)
    return None


@router.get("/api/agents/{agent_id}/process-logs")
async def agent_process_logs(
    request: Request,
    agent_id: str,
    tail: int = 200,
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Return the last *tail* lines of the worker subprocess/container logs."""
    _verify_token(request)

    # Try docker container logs first
    docker_logs_getter = getattr(runtime, "get_container_logs", None)
    if docker_logs_getter:
        content = docker_logs_getter(agent_id, tail=tail)
        if content:
            return PlainTextResponse(content)

    # Fall back to subprocess log file
    log_path = _resolve_worker_log(runtime, agent_id)
    if not log_path or not log_path.exists():
        return PlainTextResponse(
            "No subprocess log file found. Agent may not be running or log path is unavailable.\n",
            status_code=200,
        )
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        content = "".join(all_lines[-tail:])
    except OSError as exc:
        return PlainTextResponse(f"Error reading log: {exc}\n", status_code=500)
    return PlainTextResponse(content)


@router.get("/api/agents/{agent_id}/process-logs/stream")
async def agent_process_logs_stream(
    request: Request,
    agent_id: str,
    runtime: AgentRuntimeBackend = Depends(get_runtime),
    process_log_store: ProcessLogStore = Depends(get_process_log_store),
):
    """SSE stream that tails the worker subprocess/container logs (like `tail -f`)."""
    _verify_token(request)

    # Check if we have docker streaming capability
    docker_stream_getter = getattr(runtime, "stream_container_logs", None)
    log_path = _resolve_worker_log(runtime, agent_id)

    async def tail_stream():
        try:
            yield {"event": "ping", "data": ""}

            # Try docker container log streaming first
            if docker_stream_getter:
                # Backlog from RAM when available (instant for reconnects)
                backlog = process_log_store.get_recent(agent_id, limit=PROCESS_LOG_TAIL_BACKLOG)
                tail_lines = 0 if backlog else PROCESS_LOG_TAIL_BACKLOG
                for line in backlog:
                    yield {
                        "event": "message",
                        "data": json.dumps({"line": line}),
                    }
                gen = docker_stream_getter(agent_id, tail=tail_lines)
                loop = asyncio.get_running_loop()

                def _next_line(g):
                    return next(g, None)

                try:
                    while True:
                        line = await loop.run_in_executor(None, _next_line, gen)
                        if line is None:
                            await asyncio.sleep(PROCESS_LOG_POLL_INTERVAL)
                            continue
                        process_log_store.append(agent_id, line)
                        yield {
                            "event": "message",
                            "data": json.dumps({"line": line}),
                        }
                except StopIteration:
                    pass
                except Exception as exc:
                    logger.warning(f"Docker log stream error for agent {agent_id}: {exc}")
                return

            # Fall back to subprocess log file
            if not log_path or not log_path.exists():
                yield {
                    "event": "message",
                    "data": json.dumps({"line": "No subprocess log file found."}),
                }
                return

            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                # Emit last N lines as backlog
                f.seek(0, 2)
                fsize = f.tell()
                block_size = min(fsize, PROCESS_LOG_BLOCK_SIZE)
                f.seek(max(0, fsize - block_size))
                backlog = f.readlines()[-PROCESS_LOG_TAIL_BACKLOG:]
                for line in backlog:
                    yield {
                        "event": "message",
                        "data": json.dumps({"line": line.rstrip("\n")}),
                    }

                # Tail new lines
                while True:
                    line = f.readline()
                    if line:
                        yield {
                            "event": "message",
                            "data": json.dumps({"line": line.rstrip("\n")}),
                        }
                    else:
                        await asyncio.sleep(PROCESS_LOG_POLL_INTERVAL)
        except (asyncio.CancelledError, GeneratorExit):
            return

    return EventSourceResponse(
        tail_stream(),
        ping=PROCESS_LOG_PING_INTERVAL,
        headers=SSE_HEADERS,
    )
