"""AgentConfigStore: single encrypted config blob per agent.

One row per agent; config_json is full config (encrypted when SECRETS_MASTER_KEY set).
"""

import json
import logging
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from clawforce.core.database import Database
from clawlib.config.helpers import (
    restore_secrets_from_existing,
    validate_channels,
    validate_providers,
)
from clawlib.config.loader import deep_merge

logger = logging.getLogger(__name__)


class AgentConfigStore:
    """CRUD for agent config (single encrypted JSON blob) in SQLite."""

    def __init__(self, db: Database, fernet: Fernet | None = None) -> None:
        self._db = db
        self._fernet = fernet

    def get_config(self, agent_id: str) -> dict | None:
        """Return full config for agent, or None if no row."""
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT config_json FROM agent_config WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        if not row:
            return None
        raw = row["config_json"]
        if self._fernet:
            raw = self._fernet.decrypt(raw.encode()).decode()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def update_config(
        self,
        agent_id: str,
        updates: dict,
        *,
        replace_keys: list[tuple[str, ...]] | None = None,
    ) -> dict:
        """Merge updates into stored config. Returns full merged config.

        When replace_keys is set (e.g. [("tools", "software")]), those paths are
        fully replaced instead of merged, so uninstalled items are removed.
        """
        now = datetime.now(timezone.utc).isoformat()
        updates = {k: v for k, v in updates.items() if k != "secrets"}
        if "channels" in updates and isinstance(updates["channels"], dict):
            updates = {**updates, "channels": validate_channels(updates["channels"])}
        if "providers" in updates and isinstance(updates["providers"], dict):
            updates = {**updates, "providers": validate_providers(updates["providers"])}

        existing = self.get_config(agent_id) or {}
        merged = deep_merge(existing, updates, replace_empty=True)
        if replace_keys:
            for path in replace_keys:
                d = updates
                for k in path:
                    d = d.get(k) if isinstance(d, dict) else None
                    if d is None:
                        break
                else:
                    target = merged
                    for k in path[:-1]:
                        target = target.setdefault(k, {})
                    target[path[-1]] = d
        merged.pop("secrets", None)
        restore_secrets_from_existing(merged, existing)

        if not self._fernet:
            logger.warning("SECRETS_MASTER_KEY not set; storing config as plain JSON (dev mode)")

        blob = json.dumps(merged)
        if self._fernet:
            blob = self._fernet.encrypt(blob.encode()).decode()
        with self._db.connection() as conn:
            conn.execute(
                """INSERT INTO agent_config (agent_id, config_json, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(agent_id) DO UPDATE SET
                     config_json = excluded.config_json,
                     updated_at = excluded.updated_at""",
                (agent_id, blob, now),
            )
        return merged

    def delete_config(self, agent_id: str) -> bool:
        """Delete config for an agent. Returns True if anything was deleted."""
        with self._db.connection() as conn:
            c = conn.execute("DELETE FROM agent_config WHERE agent_id = ?", (agent_id,))
        return c.rowcount > 0
