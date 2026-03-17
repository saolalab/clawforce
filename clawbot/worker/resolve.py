"""Resolve agent root, config path, and file service from environment.

The agent only needs AGENT_ROOT (absolute path to its data directory).
AGENT_ID is optional — defaults to the directory name.
"""

import os
from pathlib import Path

from clawbot.agent.agent_fs import AgentFS


def resolve_agent_root() -> tuple[Path, Path, str, AgentFS]:
    """Resolve agent root, config path, agent_id, and AgentFS.

    Requires AGENT_ROOT env var (set by the runtime backend or the operator).
    Returns (agent_root, config_path, agent_id, file_service).
    """
    agent_root_env = os.environ.get("AGENT_ROOT")
    if not agent_root_env:
        raise RuntimeError("AGENT_ROOT env var is required")
    agent_root = Path(agent_root_env).resolve()
    agent_id = os.environ.get("AGENT_ID") or agent_root.name
    agent_root.mkdir(parents=True, exist_ok=True)
    file_service = AgentFS(agent_root)
    return agent_root, file_service.config_path, agent_id, file_service
