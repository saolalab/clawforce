"""Tests for clawbot.core.session module."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from clawbot.core.session import Session, SessionManager


class TestSession:
    """Tests for Session dataclass."""

    def test_create_basic(self):
        """Session should create with required fields."""
        session = Session(key="telegram:123")
        assert session.key == "telegram:123"
        assert session.messages == []
        assert isinstance(session.created_at, datetime)
        assert session.last_consolidated == 0

    def test_create_with_messages(self):
        """Session should accept messages list."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        session = Session(key="test", messages=messages)
        assert len(session.messages) == 2
        assert session.messages[0]["content"] == "Hello"

    def test_add_message(self):
        """add_message should append to messages list."""
        session = Session(key="test")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")

        assert len(session.messages) == 2
        assert session.messages[0]["role"] == "user"
        assert session.messages[0]["content"] == "Hello"
        assert session.messages[1]["role"] == "assistant"

    def test_add_message_with_kwargs(self):
        """add_message should accept additional kwargs."""
        session = Session(key="test")
        session.add_message("assistant", "Using tool", tool_calls=[{"id": "1"}])

        assert "tool_calls" in session.messages[0]
        assert session.messages[0]["tool_calls"] == [{"id": "1"}]

    def test_get_history(self):
        """get_history should return messages in LLM format."""
        session = Session(key="test")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")

        history = session.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"

    def test_get_history_max_messages(self):
        """get_history should respect max_messages limit."""
        session = Session(key="test")
        for i in range(10):
            session.add_message("user", f"Message {i}")

        history = session.get_history(max_messages=5)
        assert len(history) == 5
        assert history[0]["content"] == "Message 5"

    def test_get_history_preserves_tool_metadata(self):
        """get_history should preserve tool-related fields."""
        session = Session(key="test")
        session.messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "call_1", "name": "test"}],
            }
        )
        session.messages.append(
            {
                "role": "tool",
                "content": "result",
                "tool_call_id": "call_1",
                "name": "test",
            }
        )

        history = session.get_history()
        assert "tool_calls" in history[0]
        assert "tool_call_id" in history[1]
        assert "name" in history[1]

    def test_clear(self):
        """clear should remove all messages."""
        session = Session(key="test")
        session.add_message("user", "Hello")
        session.last_consolidated = 5

        session.clear()
        assert session.messages == []
        assert session.last_consolidated == 0


class TestSessionManager:
    """Tests for SessionManager."""

    def test_init_with_workspace(self, tmp_workspace: Path):
        """SessionManager should initialize with workspace."""
        manager = SessionManager(workspace=tmp_workspace)
        assert manager.workspace == tmp_workspace
        assert manager.sessions_dir == tmp_workspace / "sessions"
        assert manager.sessions_dir.exists()

    def test_init_with_sessions_dir(self, tmp_path: Path):
        """SessionManager should initialize with sessions_dir."""
        sessions_dir = tmp_path / "custom_sessions"
        manager = SessionManager(sessions_dir=sessions_dir)
        assert manager.sessions_dir == sessions_dir
        assert sessions_dir.exists()

    def test_init_requires_path(self):
        """SessionManager should require workspace or sessions_dir."""
        with pytest.raises(ValueError, match="requires workspace or sessions_dir"):
            SessionManager()

    def test_get_or_create_new(self, tmp_workspace: Path):
        """get_or_create should create new session if not exists."""
        manager = SessionManager(workspace=tmp_workspace)
        session = manager.get_or_create("test:123")

        assert session.key == "test:123"
        assert session.messages == []

    def test_get_or_create_cached(self, tmp_workspace: Path):
        """get_or_create should return cached session."""
        manager = SessionManager(workspace=tmp_workspace)
        session1 = manager.get_or_create("test:123")
        session1.add_message("user", "Hello")

        session2 = manager.get_or_create("test:123")
        assert session1 is session2
        assert len(session2.messages) == 1

    def test_save_and_load(self, tmp_workspace: Path):
        """save should persist and load should restore session."""
        manager = SessionManager(workspace=tmp_workspace)
        session = manager.get_or_create("test:123")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")

        manager.save(session)
        manager.invalidate("test:123")

        loaded = manager.get_or_create("test:123")
        assert len(loaded.messages) == 2
        assert loaded.messages[0]["content"] == "Hello"

    def test_save_creates_jsonl_file(self, tmp_workspace: Path):
        """save should create JSONL file."""
        manager = SessionManager(workspace=tmp_workspace)
        session = manager.get_or_create("test:123")
        session.add_message("user", "Hello")

        manager.save(session)

        session_file = manager.sessions_dir / "test_123.jsonl"
        assert session_file.exists()

        with open(session_file) as f:
            lines = f.readlines()
        assert len(lines) == 2

        metadata = json.loads(lines[0])
        assert metadata["_type"] == "metadata"

        message = json.loads(lines[1])
        assert message["role"] == "user"
        assert message["content"] == "Hello"

    def test_invalidate_removes_from_cache(self, tmp_workspace: Path):
        """invalidate should remove session from cache."""
        manager = SessionManager(workspace=tmp_workspace)
        manager.get_or_create("test:123")

        assert "test:123" in manager._cache
        manager.invalidate("test:123")
        assert "test:123" not in manager._cache

    def test_list_sessions(self, tmp_workspace: Path):
        """list_sessions should return all saved sessions."""
        manager = SessionManager(workspace=tmp_workspace)

        for key in ["telegram:1", "slack:2", "discord:3"]:
            session = manager.get_or_create(key)
            session.add_message("user", f"Hello from {key}")
            manager.save(session)

        sessions = manager.list_sessions()
        assert len(sessions) == 3
        keys = [s["key"] for s in sessions]
        assert "telegram_1" in keys or "telegram:1" in keys

    def test_persistence_across_instances(self, tmp_workspace: Path):
        """Sessions should persist across manager instances."""
        manager1 = SessionManager(workspace=tmp_workspace)
        session = manager1.get_or_create("test:123")
        session.add_message("user", "Hello")
        manager1.save(session)

        manager2 = SessionManager(workspace=tmp_workspace)
        loaded = manager2.get_or_create("test:123")

        assert len(loaded.messages) == 1
        assert loaded.messages[0]["content"] == "Hello"

    def test_last_consolidated_persists(self, tmp_workspace: Path):
        """last_consolidated should persist across saves."""
        manager = SessionManager(workspace=tmp_workspace)
        session = manager.get_or_create("test:123")
        session.last_consolidated = 10
        manager.save(session)

        manager.invalidate("test:123")
        loaded = manager.get_or_create("test:123")

        assert loaded.last_consolidated == 10

    def test_metadata_persists(self, tmp_workspace: Path):
        """Metadata should persist across saves."""
        manager = SessionManager(workspace=tmp_workspace)
        session = manager.get_or_create("test:123")
        session.metadata = {"custom_key": "custom_value"}
        manager.save(session)

        manager.invalidate("test:123")
        loaded = manager.get_or_create("test:123")

        assert loaded.metadata.get("custom_key") == "custom_value"
