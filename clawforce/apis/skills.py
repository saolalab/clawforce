"""Per-agent skills listing (enable/disable via config). All data from runtime (worker API).

Also provides skill registry search (agentskill.sh by default) and install/uninstall
(delegated to the runtime/worker which has filesystem access).
"""

import json
import logging
import os
import re
import shutil

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from clawforce.auth import get_current_user
from clawforce.core.domain.runtime import AgentRuntimeBackend, AgentRuntimeError
from clawforce.core.store.agents import AgentStore
from clawforce.deps import get_agent_store, get_runtime, get_skill_registry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["skills"])


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML-like frontmatter (key: value) from skill content."""
    if not content or not content.startswith("---"):
        return {}
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    metadata = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip("'\"")
    return metadata


def _parse_clawbot_metadata(raw: str) -> dict:
    """Parse skill metadata JSON from frontmatter (clawbot or openclaw key)."""
    try:
        data = json.loads(raw)
        return data.get("clawbot", data.get("openclaw", {})) if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _check_requirements(skill_meta: dict) -> bool:
    """Check if skill requirements are met (bins, env vars)."""
    requires = skill_meta.get("requires", {})
    for b in requires.get("bins", []):
        if not shutil.which(b):
            return False
    for env in requires.get("env", []):
        if not os.environ.get(env):
            return False
    return True


async def _list_skills_via_runtime(
    agent_id: str,
    runtime: AgentRuntimeBackend,
) -> list[dict]:
    """List skills via runtime (workspace/.agents/skills/, with config for disabled status)."""
    config_dict = await runtime.get_config(agent_id)
    disabled = set()
    if config_dict:
        skills_cfg = config_dict.get("skills") or {}
        disabled = set(skills_cfg.get("disabled") or [])

    # Collect skills from workspace/.agents/skills/<name>/SKILL.md
    skill_names: dict[str, str] = {}  # name -> relative path for reading
    workspace_files = await runtime.list_workspace(agent_id)
    for p in workspace_files:
        parts = p.split("/")
        # .agents/skills/<name>/SKILL.md = 4 parts
        if (
            len(parts) == 4
            and parts[0] == ".agents"
            and parts[1] == "skills"
            and parts[3] == "SKILL.md"
        ):
            name = parts[2]
            if name and name not in skill_names:
                skill_names[name] = p

    result = []
    for name in sorted(skill_names):
        content = await runtime.read_workspace_file(agent_id, skill_names[name])
        meta = _parse_frontmatter(content or "")
        clawbot_meta = _parse_clawbot_metadata(meta.get("metadata", ""))
        emoji = clawbot_meta.get("emoji", "")
        available = _check_requirements(clawbot_meta)
        always = bool(clawbot_meta.get("always") or meta.get("always"))
        result.append(
            {
                "name": name,
                "description": meta.get("description", name),
                "source": "workspace",
                "emoji": emoji,
                "enabled": name not in disabled,
                "available": available,
                "always": always,
            }
        )
    return result


@router.get("/api/agents/{agent_id}/skills")
async def list_agent_skills(
    agent_id: str,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """List all skills for an agent with enabled/disabled status (from worker via runtime)."""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    try:
        return await _list_skills_via_runtime(agent_id, runtime)
    except AgentRuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.get("/api/skills/search")
async def search_skills(
    q: str = "",
    limit: int = 20,
    _: dict = Depends(get_current_user),
    registry=Depends(get_skill_registry),
):
    """Search the skill registry (agentskill.sh by default)."""
    try:
        results = await registry.search_skills(q.strip(), limit=limit)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="npx not found — Node.js is required for the skill registry",
        )
    except Exception as e:
        logger.exception("Skill registry search failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Skill registry error: {e!s}",
        )
    results.sort(key=lambda s: s.get("downloads", 0), reverse=True)
    return results


class SkillInstallRequest(BaseModel):
    slug: str
    env: dict[str, str] | None = None


@router.post("/api/agents/{agent_id}/skills/install")
async def install_skill(
    agent_id: str,
    body: SkillInstallRequest,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Install a skill from the registry into the agent's workspace (delegated to runtime/worker)."""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    try:
        return await runtime.install_skill(agent_id, body.slug, body.env)
    except AgentRuntimeError as exc:
        logger.warning(f"Skill install failed: agent={agent_id} slug={body.slug} error={exc}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


class SkillUninstallRequest(BaseModel):
    slug: str


@router.post("/api/agents/{agent_id}/skills/uninstall")
async def uninstall_skill(
    agent_id: str,
    body: SkillUninstallRequest,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Remove an installed skill from the agent's workspace (delegated to runtime/worker)."""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    try:
        return await runtime.uninstall_skill(agent_id, body.slug)
    except AgentRuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
