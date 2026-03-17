"""Agent and user data models."""

import os
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Base(BaseModel):
    """Base using snake_case keys (standard Python convention)."""

    model_config = ConfigDict(populate_by_name=True, validate_assignment=True)


class AgentDef(Base):
    """Agent spec and identity (workload spec).

    Defines one logical agent; the running instance is the worker (clawbot).
    All agent data lives under ``{storage_root}/agents/{base_path}/``:
    - ``.config/agent.json`` — secrets, not agent-accessible
    - ``profiles/`` — character setup (agent read-only)
    - ``workspace/`` — collaboration sandbox (agent read/write)
    - ``.sessions/``, ``.logs/`` — internal
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_user_id: str = ""
    name: str = ""
    description: str = ""
    color: str = ""
    enabled: bool = True
    status: str = "stopped"
    base_path: str = ""  # {agent_id}/ — root for all agent data
    agent_token: str = ""
    # Execution mode: "process" (subprocess), "docker" (container), or "" (use app default)
    mode: str = ""
    onboarding_completed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="before")
    @classmethod
    def _ensure_base_path(cls, data: object) -> object:
        """Ensure base_path is set from id when empty (e.g. loaded from store)."""
        if not isinstance(data, dict):
            return data
        base = data.get("base_path") or data.get("basePath")
        agent_id = data.get("id")
        if not base and agent_id:
            data = dict(data)
            data["base_path"] = agent_id
        return data


def control_plane_overrides(agent: AgentDef) -> dict:
    """Build control_plane section for worker bootstrap (admin_url, agent_id, agent_token, heartbeat_interval)."""
    return {
        "admin_url": os.environ.get("ADMIN_PUBLIC_URL", "http://127.0.0.1:8080"),
        "agent_id": agent.id,
        "agent_token": agent.agent_token or "",
        "heartbeat_interval": 30,
    }


class UserDef(Base):
    """Admin user (role extensible later)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    password_hash: str = ""
    role: str = "admin"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
