"""Tests for AgentVariablesStore: get, upsert, delete, redaction."""

import secrets
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from clawforce.core.database import Database
from clawforce.core.store.agent_variables import AgentVariablesStore, default_git_variables


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
def store_plain(db: Database) -> AgentVariablesStore:
    """AgentVariablesStore with no encryption (plaintext mode)."""
    return AgentVariablesStore(db, fernet=None)


@pytest.fixture
def store_encrypted(db: Database) -> AgentVariablesStore:
    """AgentVariablesStore with Fernet encryption."""
    key = Fernet.generate_key()
    return AgentVariablesStore(db, fernet=Fernet(key))


# ---------------------------------------------------------------------------
# default_git_variables
# ---------------------------------------------------------------------------


def test_default_git_variables_uses_agent_name():
    v = default_git_variables("My Agent")
    assert v["GIT_AUTHOR_NAME"] == "My Agent"
    assert v["GIT_COMMITTER_NAME"] == "My Agent"
    assert "my-agent" in v["GIT_AUTHOR_EMAIL"]
    assert v["GIT_AUTHOR_EMAIL"].endswith("@clawforce.local")


def test_default_git_variables_empty_name():
    v = default_git_variables("")
    assert v["GIT_AUTHOR_NAME"] == "Clawforce Agent"
    assert "agent" in v["GIT_AUTHOR_EMAIL"]


# ---------------------------------------------------------------------------
# Plaintext mode
# ---------------------------------------------------------------------------


class TestAgentVariablesStorePlaintext:
    def test_get_nonexistent_returns_empty(self, store_plain: AgentVariablesStore, agent_id: str):
        assert store_plain.get_variables(agent_id) == {}

    def test_upsert_creates_variables(self, store_plain: AgentVariablesStore, agent_id: str):
        result = store_plain.upsert_variables(agent_id, {"MY_KEY": "my-value"})
        assert result["MY_KEY"] == "my-value"

    def test_get_variables_roundtrip(self, store_plain: AgentVariablesStore, agent_id: str):
        store_plain.upsert_variables(agent_id, {"API_KEY": "secret123", "OTHER": "val2"})
        fetched = store_plain.get_variables(agent_id)
        assert fetched["API_KEY"] == "secret123"
        assert fetched["OTHER"] == "val2"

    def test_upsert_merges(self, store_plain: AgentVariablesStore, agent_id: str):
        store_plain.upsert_variables(agent_id, {"KEY1": "val1"})
        store_plain.upsert_variables(agent_id, {"KEY2": "val2"})
        fetched = store_plain.get_variables(agent_id)
        assert fetched["KEY1"] == "val1"
        assert fetched["KEY2"] == "val2"

    def test_upsert_overwrites_existing(self, store_plain: AgentVariablesStore, agent_id: str):
        store_plain.upsert_variables(agent_id, {"KEY": "old"})
        store_plain.upsert_variables(agent_id, {"KEY": "new"})
        fetched = store_plain.get_variables(agent_id)
        assert fetched["KEY"] == "new"

    def test_strip_redacted_on_upsert(self, store_plain: AgentVariablesStore, agent_id: str):
        """Redacted values (***) are stripped and not overwritten."""
        store_plain.upsert_variables(agent_id, {"KEEP": "real", "REDACTED": "***1234"})
        fetched = store_plain.get_variables(agent_id)
        assert fetched["KEEP"] == "real"
        assert "REDACTED" not in fetched

    def test_get_variables_redact_only_secrets(
        self, store_plain: AgentVariablesStore, agent_id: str
    ):
        """Only secret keys are redacted when redact=True."""
        store_plain.upsert_variables(
            agent_id,
            {"API_KEY": "sk-xxx", "LOG_LEVEL": "debug"},  # pragma: allowlist secret
            secret_keys=frozenset({"API_KEY"}),
        )
        plain = store_plain.get_variables(agent_id, redact=False)
        assert plain["API_KEY"] == "sk-xxx"  # pragma: allowlist secret
        assert plain["LOG_LEVEL"] == "debug"
        redacted = store_plain.get_variables(agent_id, redact=True)
        assert redacted["API_KEY"].startswith("***")
        assert redacted["LOG_LEVEL"] == "debug"

    def test_upsert_with_secret_keys(self, store_plain: AgentVariablesStore, agent_id: str):
        """secret_keys is persisted and used for redaction."""
        store_plain.upsert_variables(
            agent_id,
            {"SECRET": "hide-me", "PLAIN": "show-me"},  # pragma: allowlist secret
            secret_keys=frozenset({"SECRET"}),
        )
        redacted = store_plain.get_variables(agent_id, redact=True)
        assert redacted["SECRET"].startswith("***")
        assert redacted["PLAIN"] == "show-me"

    def test_delete_variables(self, store_plain: AgentVariablesStore, agent_id: str):
        store_plain.upsert_variables(agent_id, {"X": "y"})
        deleted = store_plain.delete_variables(agent_id)
        assert deleted is True
        assert store_plain.get_variables(agent_id) == {}

    def test_delete_nonexistent_returns_false(
        self, store_plain: AgentVariablesStore, agent_id: str
    ):
        assert store_plain.delete_variables(agent_id) is False

    def test_redact_masks_values(self, store_plain: AgentVariablesStore, agent_id: str):
        store_plain.upsert_variables(
            agent_id,
            {"API_KEY": "sk-secret123", "SHORT": "x"},
            secret_keys=frozenset({"API_KEY", "SHORT"}),
        )
        redacted = store_plain.get_variables(agent_id, redact=True)
        assert redacted["API_KEY"].startswith("***")
        assert redacted["API_KEY"].endswith("t123")
        assert redacted["SHORT"] == "***"


# ---------------------------------------------------------------------------
# Encrypted mode
# ---------------------------------------------------------------------------


class TestAgentVariablesStoreEncrypted:
    def test_upsert_then_get_roundtrip(self, store_encrypted: AgentVariablesStore, agent_id: str):
        store_encrypted.upsert_variables(agent_id, {"SECRET": "supersecret"})
        fetched = store_encrypted.get_variables(agent_id)
        assert fetched["SECRET"] == "supersecret"

    def test_encrypted_blob_not_plaintext(self, db: Database, agent_id: str):
        """Stored variables_json must not contain plaintext when encrypted."""
        key = Fernet.generate_key()
        store = AgentVariablesStore(db, fernet=Fernet(key))
        store.upsert_variables(agent_id, {"API_KEY": "supersecretvalue"})

        with db.connection() as conn:
            row = conn.execute(
                "SELECT variables_json FROM agent_variables WHERE agent_id = ?", (agent_id,)
            ).fetchone()
        assert row is not None
        assert "supersecretvalue" not in row["variables_json"]

    def test_wrong_key_raises_on_decrypt(self, db: Database, agent_id: str):
        """Data encrypted with key A cannot be decrypted with key B."""
        key_a = Fernet.generate_key()
        key_b = Fernet.generate_key()
        store_a = AgentVariablesStore(db, fernet=Fernet(key_a))
        store_a.upsert_variables(agent_id, {"X": "value"})

        store_b = AgentVariablesStore(db, fernet=Fernet(key_b))
        with pytest.raises(Exception):
            store_b.get_variables(agent_id)
