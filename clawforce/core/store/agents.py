"""Agent CRUD operations backed by SQLite."""

import secrets
from datetime import datetime, timezone

from clawforce.core.database import Database
from clawforce.core.domain.agent import AgentDef
from clawforce.core.services.workspace_service import WorkspaceService
from clawforce.core.storage import StorageBackend
from clawforce.core.store.base import BaseRepository

VALID_MODES = frozenset({"", "process", "docker"})

# Identity, layout, and creation-audit fields may not be changed via update_agent().
# All other AgentDef fields are updatable (derived from model, so new fields are allowed by default).
_IMMUTABLE_FIELDS = frozenset({"id", "base_path", "created_at"})
_UPDATABLE_FIELDS = frozenset(AgentDef.model_fields) - _IMMUTABLE_FIELDS


def _serialize_for_db(model: AgentDef) -> dict:
    """Convert model to dict suitable for SQLite (bool -> int)."""
    d = model.model_dump(by_alias=False)
    d["enabled"] = 1 if d.get("enabled", True) else 0
    d["onboarding_completed"] = 1 if d.get("onboarding_completed", False) else 0
    return d


class AgentStore(BaseRepository[AgentDef]):
    """CRUD for agents persisted in SQLite."""

    table_name = "agents"
    model_class = AgentDef

    def __init__(self, db: Database, storage: StorageBackend | None = None) -> None:
        super().__init__(db)
        self._storage = storage

    def _row_to_model(self, row) -> AgentDef:
        d = dict(row)
        d["enabled"] = bool(d.get("enabled", 1))
        d["onboarding_completed"] = bool(d.get("onboarding_completed", 0))
        return self.model_class.model_validate(d)

    def list_agents(self) -> list[AgentDef]:
        return self.list_all()

    def get_agent(self, agent_id: str) -> AgentDef | None:
        return self.get_by_id(agent_id)

    def get_agent_by_token(self, token: str) -> AgentDef | None:
        """O(1) lookup by agent_token (indexed)."""
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM agents WHERE agent_token = ?", (token,)).fetchone()
            return self._row_to_model(row) if row else None

    def get_agent_by_name(self, name: str) -> AgentDef | None:
        """Case-insensitive lookup by agent name."""
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM agents WHERE LOWER(name) = LOWER(?)", (name,)
            ).fetchone()
            return self._row_to_model(row) if row else None

    def create_agent(
        self,
        name: str,
        owner_user_id: str = "",
        description: str = "",
        *,
        provision: bool = False,
        template: str | None = None,
        mode: str | None = None,
        color: str = "",
    ) -> AgentDef:
        raw_mode = (mode or "").strip().lower()
        agent_mode = raw_mode if raw_mode in VALID_MODES else ""
        agent = AgentDef(
            owner_user_id=owner_user_id,
            name=name,
            description=description,
            mode=agent_mode,
            color=color,
        )
        agent.base_path = agent.id
        agent.agent_token = secrets.token_urlsafe(32)
        d = _serialize_for_db(agent)
        cols = list(d.keys())
        placeholders = ", ".join("?" for _ in cols)
        with self._db.connection() as conn:
            conn.execute(
                f"INSERT INTO {self.table_name} ({', '.join(cols)}) VALUES ({placeholders})",
                [d[k] for k in cols],
            )
        if provision and self._storage:
            WorkspaceService(self._storage).provision(
                agent.base_path, agent_id=agent.id, template=template
            )
        return agent

    def update_agent(self, agent_id: str, **kwargs: object) -> AgentDef | None:
        agent = self.get_by_id(agent_id)
        if not agent:
            return None
        unknown = set(kwargs) - _UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"update_agent: unknown or immutable field(s): {sorted(unknown)}")
        if "mode" in kwargs and kwargs["mode"] is not None:
            raw = str(kwargs["mode"]).strip().lower()
            kwargs["mode"] = raw if raw in VALID_MODES else ""
        for k, v in kwargs.items():
            if hasattr(agent, k):
                setattr(agent, k, v)
        agent.updated_at = datetime.now(timezone.utc).isoformat()
        d = _serialize_for_db(agent)
        d.pop("id")
        set_clause = ", ".join(f"{c} = ?" for c in d)
        with self._db.connection() as conn:
            cursor = conn.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?",
                list(d.values()) + [agent_id],
            )
            if cursor.rowcount == 0:
                return None
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        return self.delete(agent_id)
