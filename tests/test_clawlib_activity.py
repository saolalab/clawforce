"""Tests for clawlib.activity module."""

import asyncio
import json
from pathlib import Path

import pytest

from clawlib.activity import ActivityEvent, ActivityLog, ActivityLogRegistry


class TestActivityEvent:
    """Tests for ActivityEvent dataclass."""

    def test_create_basic_event(self):
        """ActivityEvent should create with required fields."""
        event = ActivityEvent(
            agent_id="agent-1",
            event_type="message",
        )
        assert event.agent_id == "agent-1"
        assert event.event_type == "message"
        assert event.channel == ""
        assert event.content == ""
        assert event.timestamp is not None
        assert event.tool_name is None

    def test_create_full_event(self):
        """ActivityEvent should accept all fields."""
        event = ActivityEvent(
            agent_id="agent-1",
            event_type="tool_call",
            channel="telegram",
            content="Running shell command",
            tool_name="exec",
            tool_args_redacted={"command": "ls -la"},
            result_status="ok",
            duration_ms=150,
        )
        assert event.agent_id == "agent-1"
        assert event.event_type == "tool_call"
        assert event.channel == "telegram"
        assert event.content == "Running shell command"
        assert event.tool_name == "exec"
        assert event.tool_args_redacted == {"command": "ls -la"}
        assert event.result_status == "ok"
        assert event.duration_ms == 150


class TestActivityLog:
    """Tests for ActivityLog ring buffer and broadcast."""

    def test_init_defaults(self):
        """ActivityLog should initialize with defaults."""
        log = ActivityLog()
        assert log._max == 500
        assert len(log._buffer) == 0
        assert log._subscribers == []

    def test_init_custom_max(self):
        """ActivityLog should accept custom max_events."""
        log = ActivityLog(max_events=100)
        assert log._max == 100

    def test_emit_adds_to_buffer(self):
        """emit() should add events to the buffer."""
        log = ActivityLog()
        event = ActivityEvent(agent_id="a1", event_type="msg")
        log.emit(event)
        assert len(log._buffer) == 1
        assert log._buffer[0] == event

    def test_buffer_size_limit(self):
        """Buffer should respect max_events limit."""
        log = ActivityLog(max_events=3)
        for i in range(5):
            log.emit(ActivityEvent(agent_id="a", event_type=f"event-{i}"))
        assert len(log._buffer) == 3
        assert log._buffer[0].event_type == "event-2"
        assert log._buffer[2].event_type == "event-4"

    def test_recent_returns_latest(self):
        """recent() should return most recent events."""
        log = ActivityLog()
        for i in range(10):
            log.emit(ActivityEvent(agent_id="a", event_type=f"event-{i}"))
        recent = log.recent(limit=5)
        assert len(recent) == 5
        assert recent[0].event_type == "event-5"
        assert recent[4].event_type == "event-9"

    def test_recent_limit_larger_than_buffer(self):
        """recent() with limit > buffer size should return all events."""
        log = ActivityLog()
        for i in range(3):
            log.emit(ActivityEvent(agent_id="a", event_type=f"event-{i}"))
        recent = log.recent(limit=100)
        assert len(recent) == 3

    def test_persist_to_file(self, tmp_path: Path):
        """emit() should persist events to activity.jsonl when logs_path is set."""
        log = ActivityLog(logs_path=tmp_path)
        event = ActivityEvent(
            agent_id="agent-1",
            event_type="tool_call",
            channel="telegram",
            content="test",
            tool_name="exec",
            result_status="ok",
            duration_ms=100,
        )
        log.emit(event)

        log_file = tmp_path / "activity.jsonl"
        assert log_file.exists()

        with open(log_file) as f:
            data = json.loads(f.readline())
        assert data["agent_id"] == "agent-1"
        assert data["event_type"] == "tool_call"
        assert data["tool_name"] == "exec"
        assert data["result_status"] == "ok"
        assert data["duration_ms"] == 100

    def test_persist_creates_directory(self, tmp_path: Path):
        """Persistence should create logs directory if it doesn't exist."""
        logs_path = tmp_path / "nested" / "logs"
        log = ActivityLog(logs_path=logs_path)
        log.emit(ActivityEvent(agent_id="a", event_type="test"))
        assert logs_path.exists()

    @pytest.mark.asyncio
    async def test_subscribe_receives_events(self):
        """Subscribers should receive emitted events."""
        log = ActivityLog()
        subscriber = log.subscribe()

        event = ActivityEvent(agent_id="a", event_type="test")
        log.emit(event)

        received = await asyncio.wait_for(subscriber.__anext__(), timeout=1.0)
        assert received == event

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Multiple subscribers should all receive events."""
        log = ActivityLog()
        sub1 = log.subscribe()
        sub2 = log.subscribe()

        event = ActivityEvent(agent_id="a", event_type="test")
        log.emit(event)

        r1 = await asyncio.wait_for(sub1.__anext__(), timeout=1.0)
        r2 = await asyncio.wait_for(sub2.__anext__(), timeout=1.0)
        assert r1 == event
        assert r2 == event


class TestActivityLogRegistry:
    """Tests for ActivityLogRegistry."""

    def test_get_or_create_new(self):
        """get_or_create should create new log for unknown agent."""
        registry = ActivityLogRegistry()
        log = registry.get_or_create("agent-1")
        assert isinstance(log, ActivityLog)
        assert "agent-1" in registry._logs

    def test_get_or_create_existing(self):
        """get_or_create should return existing log for known agent."""
        registry = ActivityLogRegistry()
        log1 = registry.get_or_create("agent-1")
        log2 = registry.get_or_create("agent-1")
        assert log1 is log2

    def test_get_or_create_with_logs_path(self, tmp_path: Path):
        """get_or_create should pass logs_path to new ActivityLog."""
        registry = ActivityLogRegistry()
        log = registry.get_or_create("agent-1", logs_path=tmp_path)
        log.emit(ActivityEvent(agent_id="agent-1", event_type="test"))
        assert (tmp_path / "activity.jsonl").exists()

    def test_reset_clears_events(self):
        """reset() should clear old events and return fresh log."""
        registry = ActivityLogRegistry()
        log1 = registry.get_or_create("agent-1")
        log1.emit(ActivityEvent(agent_id="agent-1", event_type="old"))
        assert len(log1._buffer) == 1

        log2 = registry.reset("agent-1")
        assert log2 is not log1
        assert len(log2._buffer) == 0
        assert registry._logs["agent-1"] is log2

    def test_reset_with_logs_path(self, tmp_path: Path):
        """reset() should accept logs_path for new log."""
        registry = ActivityLogRegistry()
        log = registry.reset("agent-1", logs_path=tmp_path)
        log.emit(ActivityEvent(agent_id="agent-1", event_type="test"))
        assert (tmp_path / "activity.jsonl").exists()

    @pytest.mark.asyncio
    async def test_subscribe(self):
        """subscribe() should return iterator from agent's log."""
        registry = ActivityLogRegistry()
        subscriber = registry.subscribe("agent-1")

        log = registry.get_or_create("agent-1")
        event = ActivityEvent(agent_id="agent-1", event_type="test")
        log.emit(event)

        received = await asyncio.wait_for(subscriber.__anext__(), timeout=1.0)
        assert received == event

    def test_multiple_agents(self):
        """Registry should handle multiple agents independently."""
        registry = ActivityLogRegistry()
        log1 = registry.get_or_create("agent-1")
        log2 = registry.get_or_create("agent-2")

        log1.emit(ActivityEvent(agent_id="agent-1", event_type="event-1"))
        log2.emit(ActivityEvent(agent_id="agent-2", event_type="event-2"))

        assert len(log1._buffer) == 1
        assert len(log2._buffer) == 1
        assert log1._buffer[0].event_type == "event-1"
        assert log2._buffer[0].event_type == "event-2"
