"""AgentVariablesStore: env variables (KEY=value) for process/container injection.

Maps to the Variables tab in the UI. Runtime fetches from here when starting agents.
Same encryption pattern as AgentConfigStore (Fernet when SECRETS_MASTER_KEY set).
Storage format: { "K": { "value": "v", "secret": bool } }
"""

import json
import logging
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from clawforce.core.database import Database

logger = logging.getLogger(__name__)


def default_git_variables(agent_name: str) -> dict[str, str]:
    """Default Variables for git commit. Uses agent name for GIT_AUTHOR_NAME."""
    name = (agent_name or "Clawforce Agent").strip() or "Clawforce Agent"
    local = (
        "".join(c if c.isalnum() or c in "-_" else "-" for c in name.lower()).strip("-") or "agent"
    )
    email = f"{local}@clawforce.local"
    return {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }


def _parse_stored(data: dict) -> dict[str, dict]:
    """Parse stored blob into { K: { value, secret } }. Malformed/old data returns {}."""
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict] = {}
    for k, v in data.items():
        if not k:
            continue
        if isinstance(v, dict) and "value" in v:
            val = v.get("value")
            secret = v.get("secret", True)
            if val is not None:
                out[k] = {"value": str(val), "secret": bool(secret)}
        elif isinstance(v, str) and v:
            out[k] = {"value": v, "secret": True}
    return out


def _to_flat(data: dict[str, dict], redact: bool = False) -> dict[str, str]:
    """Extract flat dict. redact=True masks secret values."""
    out: dict[str, str] = {}
    for k, v in data.items():
        val = v.get("value", "")
        if not isinstance(val, str):
            continue
        if redact and v.get("secret", True):
            out[k] = "***" + val[-4:] if len(val) > 4 else "***"
        else:
            out[k] = val
    return out


def _strip_redacted(variables: dict[str, str]) -> dict[str, str]:
    """Omit keys whose values are redacted placeholders (***)."""
    return {k: v for k, v in variables.items() if not (isinstance(v, str) and v.startswith("***"))}


class AgentVariablesStore:
    """CRUD for agent env variables (encrypted JSON blob) in SQLite."""

    def __init__(self, db: Database, fernet: Fernet | None = None) -> None:
        self._db = db
        self._fernet = fernet

    def _encrypt_blob(self, data: str) -> str:
        if self._fernet:
            return self._fernet.encrypt(data.encode()).decode()
        return data

    def _decrypt_blob(self, stored: str | None) -> str:
        if not stored:
            return "{}"
        if self._fernet:
            return self._fernet.decrypt(stored.encode()).decode()
        return stored

    def get_variables(self, agent_id: str, *, redact: bool = False) -> dict[str, str]:
        """Return env vars for agent. redact=True masks secret values for API."""
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT variables_json FROM agent_variables WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        if not row:
            return {}
        raw = row["variables_json"]
        json_str = self._decrypt_blob(raw)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return {}
        parsed = _parse_stored(data)
        return _to_flat(parsed, redact=redact)

    def upsert_variables(
        self,
        agent_id: str,
        variables: dict[str, str],
        *,
        secret_keys: frozenset[str] = frozenset(),
    ) -> dict[str, str]:
        """Deep-merge variables into stored. Strip redacted. Returns merged flat dict."""
        now = datetime.now(timezone.utc).isoformat()
        clean = _strip_redacted(variables)

        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT variables_json FROM agent_variables WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        existing: dict[str, dict] = {}
        if row:
            try:
                json_str = self._decrypt_blob(row["variables_json"])
                data = json.loads(json_str)
                existing = _parse_stored(data)
            except (json.JSONDecodeError, TypeError):
                existing = {}

        for k, v in clean.items():
            if not k or not v:
                continue
            existing[k] = {"value": v, "secret": k in secret_keys}

        merged = {k: v for k, v in existing.items() if k and v.get("value")}

        if not self._fernet:
            logger.warning("SECRETS_MASTER_KEY not set; storing variables as plain JSON (dev mode)")

        blob = self._encrypt_blob(json.dumps(merged))
        with self._db.connection() as conn:
            conn.execute(
                """INSERT INTO agent_variables (agent_id, variables_json, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(agent_id) DO UPDATE SET
                     variables_json = excluded.variables_json,
                     updated_at = excluded.updated_at""",
                (agent_id, blob, now),
            )
        return _to_flat(merged, redact=False)

    def delete_variables(self, agent_id: str) -> bool:
        """Delete variables for an agent. Returns True if anything was deleted."""
        with self._db.connection() as conn:
            c = conn.execute("DELETE FROM agent_variables WHERE agent_id = ?", (agent_id,))
        return c.rowcount > 0
