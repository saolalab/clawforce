"""Tests for AgentConfigStore: get_config, update_config, single encrypted blob."""

import secrets
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from clawforce.core.database import Database
from clawforce.core.store.agent_config import AgentConfigStore


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture
def agent_id(db: Database) -> str:
    """Create a real agent row so FK constraints are satisfied."""
    aid = "test-agent-001"
    now = datetime.now(timezone.utc).isoformat()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO agents (id, name, base_path, agent_token, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (aid, "Test Agent", aid, secrets.token_urlsafe(16), now, now),
        )
    return aid


@pytest.fixture
def store_plain(db: Database) -> AgentConfigStore:
    return AgentConfigStore(db, fernet=None)


@pytest.fixture
def store_encrypted(db: Database) -> AgentConfigStore:
    return AgentConfigStore(db, fernet=Fernet(Fernet.generate_key()))


class TestAgentConfigStorePlaintext:
    def test_get_nonexistent_returns_none(self, store_plain: AgentConfigStore, agent_id: str):
        assert store_plain.get_config(agent_id) is None

    def test_update_creates_config(self, store_plain: AgentConfigStore, agent_id: str):
        result = store_plain.update_config(agent_id, {"agents": {"defaults": {"model": "gpt-4"}}})
        assert result["agents"]["defaults"]["model"] == "gpt-4"

    def test_get_config_roundtrip(self, store_plain: AgentConfigStore, agent_id: str):
        store_plain.update_config(agent_id, {"agents": {"defaults": {"model": "gpt-4"}}})
        fetched = store_plain.get_config(agent_id)
        assert fetched is not None
        assert fetched["agents"]["defaults"]["model"] == "gpt-4"

    def test_update_merges(self, store_plain: AgentConfigStore, agent_id: str):
        store_plain.update_config(agent_id, {"agents": {"defaults": {"model": "gpt-4"}}})
        store_plain.update_config(agent_id, {"agents": {"defaults": {"temperature": 0.5}}})
        fetched = store_plain.get_config(agent_id)
        assert fetched["agents"]["defaults"]["model"] == "gpt-4"
        assert fetched["agents"]["defaults"]["temperature"] == 0.5

    def test_full_config_includes_providers_channels(
        self, store_plain: AgentConfigStore, agent_id: str
    ):
        store_plain.update_config(
            agent_id,
            {
                "providers": {"openai": {"api_key": "sk-test"}},
                "channels": {"slack": {"bot_token": "xoxb-test"}},
            },
        )
        config = store_plain.get_config(agent_id)
        assert config["providers"]["openai"]["api_key"] == "sk-test"
        assert config["channels"]["slack"]["bot_token"] == "xoxb-test"

    def test_update_overwrites_secret(self, store_plain: AgentConfigStore, agent_id: str):
        store_plain.update_config(agent_id, {"providers": {"openai": {"api_key": "old-key"}}})
        store_plain.update_config(agent_id, {"providers": {"openai": {"api_key": "new-key"}}})
        config = store_plain.get_config(agent_id)
        assert config["providers"]["openai"]["api_key"] == "new-key"

    def test_delete_config(self, store_plain: AgentConfigStore, agent_id: str):
        store_plain.update_config(agent_id, {"agents": {"defaults": {"model": "gpt-4"}}})
        assert store_plain.delete_config(agent_id) is True
        assert store_plain.get_config(agent_id) is None

    def test_delete_nonexistent_returns_false(self, store_plain: AgentConfigStore, agent_id: str):
        assert store_plain.delete_config(agent_id) is False

    def test_channel_fields_preserved(self, store_plain: AgentConfigStore, agent_id: str):
        store_plain.update_config(
            agent_id,
            {
                "channels": {
                    "slack": {
                        "enabled": True,
                        "bot_token": "xoxb-test",
                        "app_token": "xapp-test",
                        "reply_in_thread": True,
                    }
                }
            },
        )
        config = store_plain.get_config(agent_id)
        assert config["channels"]["slack"]["bot_token"] == "xoxb-test"
        assert config["channels"]["slack"]["app_token"] == "xapp-test"
        assert config["channels"]["slack"]["enabled"] is True

    def test_replace_keys_removes_uninstalled_software(
        self, store_plain: AgentConfigStore, agent_id: str
    ):
        """replace_keys fully replaces tools.software so uninstalled items are removed."""
        store_plain.update_config(
            agent_id,
            {
                "tools": {
                    "software": {
                        "foo": {"package": "foo-pkg", "command": "foo"},
                        "bar": {"package": "bar-pkg", "command": "bar"},
                    }
                }
            },
        )
        # Simulate uninstall of "bar" - pass only remaining software
        store_plain.update_config(
            agent_id,
            {"tools": {"software": {"foo": {"package": "foo-pkg", "command": "foo"}}}},
            replace_keys=[("tools", "software")],
        )
        config = store_plain.get_config(agent_id)
        assert "foo" in config["tools"]["software"]
        assert "bar" not in config["tools"]["software"]

    def test_restore_secrets_from_existing(self, store_plain: AgentConfigStore, agent_id: str):
        """Redacted/empty updates do not overwrite existing secrets."""
        store_plain.update_config(
            agent_id,
            {
                "channels": {
                    "slack": {"enabled": True, "bot_token": "xoxb-real", "app_token": "xapp-real"}
                },
                "providers": {"openai": {"api_key": "sk-real"}},
            },
        )
        store_plain.update_config(
            agent_id,
            {"channels": {"slack": {"enabled": False}}, "providers": {"openai": {}}},
        )
        config = store_plain.get_config(agent_id)
        assert config["channels"]["slack"]["bot_token"] == "xoxb-real"
        assert config["channels"]["slack"]["app_token"] == "xapp-real"
        assert config["providers"]["openai"]["api_key"] == "sk-real"
        assert config["channels"]["slack"]["enabled"] is False


class TestAgentConfigStoreEncrypted:
    def test_update_then_get_roundtrip(self, store_encrypted: AgentConfigStore, agent_id: str):
        store_encrypted.update_config(agent_id, {"providers": {"openai": {"api_key": "sk-secret"}}})
        config = store_encrypted.get_config(agent_id)
        assert config["providers"]["openai"]["api_key"] == "sk-secret"

    def test_encrypted_blob_not_plaintext(self, db: Database, agent_id: str):
        store = AgentConfigStore(db, fernet=Fernet(Fernet.generate_key()))
        store.update_config(agent_id, {"providers": {"openai": {"api_key": "supersecretvalue"}}})
        with db.connection() as conn:
            row = conn.execute(
                "SELECT config_json FROM agent_config WHERE agent_id = ?", (agent_id,)
            ).fetchone()
        assert row is not None
        assert "supersecretvalue" not in row["config_json"]

    def test_wrong_key_raises_on_decrypt(self, db: Database, agent_id: str):
        store_a = AgentConfigStore(db, fernet=Fernet(Fernet.generate_key()))
        store_a.update_config(agent_id, {"providers": {"openai": {"api_key": "value"}}})
        store_b = AgentConfigStore(db, fernet=Fernet(Fernet.generate_key()))
        with pytest.raises(Exception):
            store_b.get_config(agent_id)

    def test_merge_preserves_existing(self, store_encrypted: AgentConfigStore, agent_id: str):
        store_encrypted.update_config(agent_id, {"providers": {"openai": {"api_key": "key-one"}}})
        store_encrypted.update_config(
            agent_id, {"providers": {"anthropic": {"api_key": "key-two"}}}
        )
        config = store_encrypted.get_config(agent_id)
        assert config["providers"]["openai"]["api_key"] == "key-one"
        assert config["providers"]["anthropic"]["api_key"] == "key-two"
