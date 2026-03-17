"""Worker-side provisioning: ensure agent root has minimal layout and optional templates."""

import json
import shutil
from pathlib import Path

from clawbot.templates.resolver import get_profile_template_dir, get_workspace_template_dir


def provision_agent_root(agent_root: Path, agent_id: str = "", role: str = "default") -> None:
    """Ensure agent root has .config/, profiles/, workspace/, .sessions/, .logs/.

    If role is given and templates exist, copies profile and workspace templates.
    Config from profile template (config/agent.yaml) is written to .config/agent.json.
    """
    agent_root = Path(agent_root)
    agent_root.mkdir(parents=True, exist_ok=True)
    config_dir = agent_root / ".config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "agent.json"

    profile_tpl = get_profile_template_dir(role)
    if profile_tpl:
        for path in profile_tpl.rglob("*"):
            if path.is_file():
                rel = path.relative_to(profile_tpl)
                key = str(rel).replace("\\", "/")
                if key.startswith("config/"):
                    if agent_id:
                        dest_name = rel.name.replace(".yaml", ".json").replace(".yml", ".json")
                        dest = config_dir / dest_name
                        if path.suffix in (".yaml", ".yml"):
                            import yaml

                            data = yaml.safe_load(path.read_text()) or {}
                            dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
                        else:
                            shutil.copy2(path, dest)
                else:
                    dest = agent_root / "profiles" / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)

    workspace_tpl = get_workspace_template_dir(role)
    if workspace_tpl:
        for path in workspace_tpl.rglob("*"):
            if path.is_file():
                rel = path.relative_to(workspace_tpl)
                key = str(rel).replace("\\", "/")
                # Skills: workspace/skills/<name>/ -> workspace/.agents/skills/<name>/
                if key.startswith("skills/") and "/" in key:
                    parts = key.split("/")
                    skill_name = parts[1]
                    rest = "/".join(parts[2:])
                    dest = agent_root / "workspace" / ".agents" / "skills" / skill_name / rest
                # Memory: workspace/memory/ -> workspace/.agents/memory/
                elif key.startswith("memory/"):
                    rest = key.removeprefix("memory/")
                    dest = agent_root / "workspace" / ".agents" / "memory" / rest
                # HEARTBEAT: workspace/HEARTBEAT.md -> workspace/.agents/HEARTBEAT.md
                elif key == "HEARTBEAT.md":
                    dest = agent_root / "workspace" / ".agents" / "HEARTBEAT.md"
                else:
                    dest = agent_root / "workspace" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)

    if not config_file.exists():
        minimal = {"agents": {"defaults": {}}}
        if agent_id:
            minimal.setdefault("control_plane", {})["agent_id"] = agent_id
        config_file.write_text(json.dumps(minimal, indent=2), encoding="utf-8")

    for sub in ("profiles", "workspace", ".sessions", ".logs"):
        (agent_root / sub).mkdir(parents=True, exist_ok=True)
