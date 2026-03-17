"""SkillRegistry implementation using agentskill.sh API (99,000+ skills with full metadata)."""

import asyncio
import os
from pathlib import Path
from urllib.parse import urlencode

import httpx

_SKILLS_TIMEOUT = 60
_AGENTSKILL_API = "https://agentskill.sh/api/skills"


def _skill_name_from_path(path: str) -> str:
    """Extract skill name from githubPath like skills/pdf/SKILL.md or .gemini/skills/docx/SKILL.md."""
    parts = path.replace("\\", "/").split("/")
    for i, p in enumerate(parts):
        if p == "SKILL.md" and i > 0:
            return parts[i - 1]
    return parts[-2] if len(parts) >= 2 else ""


def _api_entry_to_skill(entry: dict) -> dict:
    """Convert agentskill.sh API entry to MarketplaceSkill shape."""
    slug_api = entry.get("slug", "")
    owner = entry.get("githubOwner", entry.get("owner", ""))
    repo = entry.get("githubRepo", "")
    path = entry.get("githubPath", "")
    skill_name = _skill_name_from_path(path) or entry.get("name", slug_api.split("/")[-1])
    # Install slug for npx skills: owner/repo@skill_name
    install_slug = f"{owner}/{repo}@{skill_name}" if repo else slug_api
    return {
        "slug": install_slug,
        "name": entry.get("name", skill_name),
        "description": (entry.get("description") or "")[:500],
        "version": "",
        "author": owner,
        "downloads": int(entry.get("githubStars", entry.get("topScore", 0)) or 0),
        "categories": [entry["category"]]
        if entry.get("category")
        else (entry.get("skillTypes") or []),
        "license": "",
        "homepage": f"https://agentskill.sh/@{slug_api}",
        "repository": entry.get(
            "repositoryUrl", f"https://github.com/{owner}/{repo}" if repo else ""
        ),
        "required_env": [],
    }


async def _fetch_agentskill_api(query: str, limit: int) -> list[dict]:
    """Fetch skills from agentskill.sh API. Uses section=top for browse, q for search."""
    params = {
        "page": 1,
        "limit": min(limit, 50),
        "includeTotal": "true",
    }
    if query.strip():
        params["q"] = query.strip()
    else:
        params["section"] = "top"
        params["category"] = "development"
    url = f"{_AGENTSKILL_API}?{urlencode(params)}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []
    items = data.get("data", [])
    return [_api_entry_to_skill(e) for e in items if isinstance(e, dict)]


async def _run_skills(
    *args: str, cwd: str | Path | None = None, env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """Run skills CLI via npx. Returns (returncode, stdout, stderr)."""
    cmd = ["npx", "--yes", "skills@latest", *args]
    merged_env = {**os.environ, "DISABLE_TELEMETRY": "1", "NO_COLOR": "1", **(env or {})}
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_SKILLS_TIMEOUT)
    return (
        proc.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


class SkillsShRegistry:
    """SkillRegistry implementation using agentskill.sh API (99,000+ skills with full metadata)."""

    async def search_skills(self, query: str, limit: int) -> list[dict]:
        """Search skills via agentskill.sh API. Returns skills with description, category, etc."""
        results = await _fetch_agentskill_api(query.strip() or "skill", limit)
        return results

    async def install_skill(
        self,
        slug: str,
        dest: Path,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        """Install a skill via the skills CLI into dest/.agents/skills/<name>/."""
        dest = Path(dest)

        # Run from workspace root. Use cursor (installs to dest/.agents/skills/<name>/).
        if "@" in slug:
            owner_repo, skill_name = slug.rsplit("@", 1)
            args = ["add", owner_repo, "--skill", skill_name, "--agent", "cursor", "-y"]
        else:
            args = ["add", slug, "--agent", "cursor", "-y"]

        rc, stdout, stderr = await _run_skills(*args, cwd=dest, env=env or {})
        return rc, stdout, stderr
