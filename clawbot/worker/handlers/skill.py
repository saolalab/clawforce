"""Skill handlers for installing and uninstalling skills from the registry."""

import logging
import shutil

from clawbot.agent.agent_fs import AgentFS
from clawbot.worker.handlers.schema import (
    InstallSkillRequest,
    SkillResultData,
    UninstallSkillRequest,
)
from clawlib.registry import get_skill_registry

logger = logging.getLogger(__name__)


def _slug_to_skill_name(slug: str) -> str:
    """Extract skill directory name from slug (owner/repo@skill-name -> skill-name)."""
    if "@" in slug:
        return slug.rsplit("@", 1)[1]
    return slug.replace("/", "_").replace(".", "_") or "skill"


async def handle_install_skill(file_service: AgentFS, req: InstallSkillRequest) -> dict:
    workspace_dir = file_service.workspace_path
    workspace_dir.mkdir(parents=True, exist_ok=True)
    registry = get_skill_registry()
    rc, stdout, stderr = await registry.install_skill(req.slug, workspace_dir, req.env or None)
    if rc != 0:
        err_msg = (stderr or stdout or "npx skills exited with non-zero code").strip()[:500]
        logger.warning("Skill install failed: slug=%s rc=%s stderr=%s", req.slug, rc, stderr[:300])
        raise RuntimeError(f"Install failed: {err_msg}")
    installed_slug = _slug_to_skill_name(req.slug)
    return {"data": SkillResultData(slug=installed_slug, message=stdout.strip()[:200]).model_dump()}


async def handle_uninstall_skill(file_service: AgentFS, req: UninstallSkillRequest) -> dict:
    workspace = file_service.workspace_path
    skill_name = _slug_to_skill_name(req.slug)
    skill_dir = workspace / ".agents" / "skills" / skill_name
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill '{req.slug}' not found")
    shutil.rmtree(skill_dir, ignore_errors=True)
    return {"data": SkillResultData(slug=req.slug).model_dump()}
