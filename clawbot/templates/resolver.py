"""Resolve template directory for provisioning. Checks env, then role, then default."""

import os
from pathlib import Path


def get_template_dir(role: str = "default") -> Path | None:
    """Resolve template directory for the given role.

    1. CLAWBOT_TEMPLATE_DIR env var (exact path)
    2. clawbot/templates/{role}/ (package-relative)
    3. clawbot/templates/default/
    """
    env_path = os.environ.get("CLAWBOT_TEMPLATE_DIR")
    if env_path:
        p = Path(env_path).resolve()
        if p.is_dir():
            return p

    here = Path(__file__).resolve().parent
    role_dir = here / role
    if role_dir.is_dir():
        return role_dir
    default_dir = here / "default"
    if default_dir.is_dir():
        return default_dir
    return None


def get_profile_template_dir(role: str = "default") -> Path | None:
    """Profile template dir: {template_dir}/profile/."""
    base = get_template_dir(role)
    if base is None:
        return None
    profile = base / "profile"
    return profile if profile.is_dir() else None


def get_workspace_template_dir(role: str = "default") -> Path | None:
    """Workspace template dir: {template_dir}/workspace/."""
    base = get_template_dir(role)
    if base is None:
        return None
    workspace = base / "workspace"
    return workspace if workspace.is_dir() else None
