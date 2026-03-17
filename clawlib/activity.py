"""Activity event log, broadcast, and registry.

Shared by both the agent worker (local ring buffer) and the admin
(per-agent registry) so that the same data types flow end-to-end.
Optional persistence to .logs/activity.jsonl with tool-call event details.

Memory / storage safety:
- In-memory ring buffer uses ``collections.deque(maxlen=…)`` — bounded.
- Subscriber queues are bounded (``maxsize=2000``); slow consumers drop oldest.
- JSONL files are rotated when they exceed ``_LOG_ROTATE_BYTES`` (default 10 MB).
- ``ActivityLogRegistry.remove()`` lets callers evict stopped agents.
"""

import asyncio
import json
import os
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

_SUBSCRIBER_QUEUE_MAX = 2000
_LOG_ROTATE_BYTES = 10 * 1024 * 1024  # 10 MB
_LOG_KEEP_ROTATED = 2  # keep activity.1.jsonl and activity.2.jsonl


@dataclass
class ActivityEvent:
    """Single activity event for an agent (message, tool call, etc.)."""

    agent_id: str
    event_type: str
    channel: str = ""
    content: str = ""
    plan_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tool_name: str | None = None
    tool_args_redacted: dict[str, Any] | None = None
    result_status: str | None = None  # "ok" | "error"
    duration_ms: int | None = None
    event_id: str | None = None  # Unique id for deduplication (reconnect-safe)


class ActivityLog:
    """In-memory ring buffer of activity events + broadcast to SSE subscribers.

    When logs_path is set, each event is appended to {logs_path}/activity.jsonl (JSONL).
    The file is rotated when it exceeds ``_LOG_ROTATE_BYTES``.
    """

    def __init__(self, max_events: int = 500, logs_path: Path | None = None) -> None:
        self._max = max_events
        self._buffer: deque[ActivityEvent] = deque(maxlen=max_events)
        self._subscribers: list[asyncio.Queue[ActivityEvent | None]] = []
        self._logs_path = Path(logs_path) if logs_path else None

    def emit(self, event: ActivityEvent) -> None:
        if event.event_id is None:
            event.event_id = uuid.uuid4().hex
        self._buffer.append(event)
        if self._logs_path:
            self._persist(event)
        dead: list[asyncio.Queue[ActivityEvent | None]] = []
        for q in self._subscribers:
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.remove(q)

    def _persist(self, event: ActivityEvent) -> None:
        """Append one JSON line to activity.jsonl, rotating when too large."""
        try:
            self._logs_path.mkdir(parents=True, exist_ok=True)
            path = self._logs_path / "activity.jsonl"
            if path.exists() and path.stat().st_size >= _LOG_ROTATE_BYTES:
                self._rotate(path)
            out: dict[str, Any] = {
                "agent_id": event.agent_id,
                "event_type": event.event_type,
                "channel": event.channel,
                "content": event.content,
                "plan_id": event.plan_id,
                "timestamp": event.timestamp,
            }
            if event.tool_name is not None:
                out["tool_name"] = event.tool_name
            if event.tool_args_redacted is not None:
                out["tool_args_redacted"] = event.tool_args_redacted
            if event.result_status is not None:
                out["result_status"] = event.result_status
            if event.duration_ms is not None:
                out["duration_ms"] = event.duration_ms
            if event.event_id is not None:
                out["event_id"] = event.event_id
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(out, ensure_ascii=False) + "\n")
        except Exception:
            pass

    @staticmethod
    def _rotate(path: Path) -> None:
        """Rotate activity.jsonl → activity.1.jsonl → activity.2.jsonl, drop oldest."""
        parent = path.parent
        for i in range(_LOG_KEEP_ROTATED, 0, -1):
            src = parent / f"activity.{i}.jsonl" if i > 0 else path
            dst = parent / f"activity.{i + 1}.jsonl"
            if i == _LOG_KEEP_ROTATED:
                src_check = parent / f"activity.{i}.jsonl"
                if src_check.exists():
                    os.remove(src_check)
            elif src.exists():
                os.rename(src, dst)
        if path.exists():
            os.rename(path, parent / "activity.1.jsonl")

    def recent(self, limit: int = 100) -> list[ActivityEvent]:
        return list(self._buffer)[-limit:]

    def subscribe(self) -> AsyncIterator[ActivityEvent]:
        q: asyncio.Queue[ActivityEvent | None] = asyncio.Queue(maxsize=_SUBSCRIBER_QUEUE_MAX)
        self._subscribers.append(q)

        async def gen() -> AsyncIterator[ActivityEvent]:
            try:
                while True:
                    ev = await q.get()
                    if ev is None:
                        break
                    yield ev
            finally:
                if q in self._subscribers:
                    self._subscribers.remove(q)

        return gen()


class ActivityLogRegistry:
    """Registry of activity logs per agent (used on the admin side)."""

    def __init__(self) -> None:
        self._logs: dict[str, ActivityLog] = {}

    def get_or_create(self, agent_id: str, logs_path: Path | None = None) -> ActivityLog:
        if agent_id not in self._logs:
            self._logs[agent_id] = ActivityLog(logs_path=logs_path)
        return self._logs[agent_id]

    def reset(self, agent_id: str, logs_path: Path | None = None) -> ActivityLog:
        """Clear old events and return a fresh ActivityLog for the agent."""
        self._logs[agent_id] = ActivityLog(logs_path=logs_path)
        return self._logs[agent_id]

    def remove(self, agent_id: str) -> None:
        """Evict an agent's log entirely (e.g. after the agent stops)."""
        self._logs.pop(agent_id, None)

    def subscribe(self, agent_id: str) -> AsyncIterator[ActivityEvent]:
        return self.get_or_create(agent_id).subscribe()
