"""Role template endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from clawforce.auth import get_current_user

_ROOT = Path(__file__).resolve().parents[3]
_ROLES_TEMPLATES_DIR = _ROOT / "marketplace" / "roles"

router = APIRouter(tags=["templates"])


def _iter_role_templates():
    """Yield role template dirs, excluding internal dirs like _shared."""
    if not _ROLES_TEMPLATES_DIR.is_dir():
        return
    for entry in sorted(_ROLES_TEMPLATES_DIR.iterdir()):
        if entry.is_dir() and not entry.name.startswith((".", "_")):
            yield entry


@router.get("/api/templates")
def list_templates(_: dict = Depends(get_current_user)):
    """List available agent role templates. Default is always first."""
    templates = [
        {"value": entry.name, "label": entry.name.replace("-", " ").title()}
        for entry in _iter_role_templates()
    ]
    templates.sort(key=lambda t: (0 if t["value"] == "default" else 1, t["label"].lower()))
    return templates


@router.get("/api/templates/{template_id}")
def get_template_detail(
    template_id: str,
    _: dict = Depends(get_current_user),
):
    """Return file setup (profile + workspace) with contents for a role template."""
    role_dir = _ROLES_TEMPLATES_DIR / template_id
    if not role_dir.is_dir() or template_id.startswith((".", "_")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    def _collect_files_with_content(base: Path) -> list[dict]:
        out = []
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    rel = str(p.relative_to(base)).replace("\\", "/")
                    try:
                        content = p.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        content = "(binary or unreadable)"
                    out.append({"path": rel, "content": content})
        return out

    profile_dir = role_dir / "profile"
    workspace_dir = role_dir / "workspace"
    label = template_id.replace("-", " ").title()

    return {
        "value": template_id,
        "label": label,
        "profileFiles": _collect_files_with_content(profile_dir),
        "workspaceFiles": _collect_files_with_content(workspace_dir),
    }
