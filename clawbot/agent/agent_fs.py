"""Unified filesystem access for the agent runtime.

Access rules for agent tools:
- workspace/: read + write (agent sandbox)
- profiles/:  read-only (PermissionError on write)
- .config/, .sessions/, .logs/: hidden, inaccessible via tools
"""

import shutil
from pathlib import Path


class AgentFS:
    """Single filesystem abstraction for the worker. All agent tools and runtime use this."""

    def __init__(self, agent_root: Path) -> None:
        self.agent_root = Path(agent_root)
        self.workspace_path = self.agent_root / "workspace"
        self.profile_path = self.agent_root / "profiles"
        self.config_path = self.agent_root / ".config" / "agent.json"
        self.sessions_path = self.agent_root / ".sessions"
        self.logs_path = self.agent_root / ".logs"
        self._crons_path = self.profile_path / "crons"

    def resolve_read(self, path: str) -> Path:
        """Resolve a path for reading. Allows workspace/, profiles/. Raises PermissionError otherwise."""
        path = path.lstrip("/").replace("\\", "/")
        if ".." in path or path.startswith("/"):
            raise PermissionError("Path must be relative and not contain ..")
        if not (path.startswith("workspace/") or path.startswith("profiles/")):
            path = "workspace/" + path
        resolved = (self.agent_root / path).resolve()
        root_res = self.agent_root.resolve()
        if not resolved.is_relative_to(root_res):
            raise PermissionError(f"Path {path} is outside agent root")
        ws_res = self.workspace_path.resolve()
        pf_res = self.profile_path.resolve()
        if not (resolved.is_relative_to(ws_res) or resolved.is_relative_to(pf_res)):
            raise PermissionError("Path is not in workspace/ or profiles/")
        return resolved

    def resolve_write(self, path: str) -> Path:
        """Resolve a path for writing. Allows workspace/. Raises PermissionError for profiles/."""
        path = path.lstrip("/").replace("\\", "/")
        if ".." in path or path.startswith("/"):
            raise PermissionError("Path must be relative and not contain ..")
        if not (path.startswith("workspace/") or path == "workspace"):
            path = "workspace/" + path
        resolved = (self.agent_root / path).resolve()
        if not resolved.is_relative_to(self.agent_root.resolve()):
            raise PermissionError(f"Path {path} is outside agent root")
        if resolved.is_relative_to(self.profile_path.resolve()):
            raise PermissionError("profiles/ is read-only; write only to workspace/")
        ws_res = self.workspace_path.resolve()
        if not resolved.is_relative_to(ws_res):
            raise PermissionError("Only paths under workspace/ can be written to")
        return resolved

    def list_dir(self, path: str) -> list[str]:
        """List directory contents. Allows workspace/, profiles/. Empty path = logical root."""
        path = path.strip("/").replace("\\", "/") or "."
        if ".." in path:
            raise PermissionError("Path must not contain ..")
        root_res = self.agent_root.resolve()
        ws_res = self.workspace_path.resolve()
        pf_res = self.profile_path.resolve()
        if path in (".", ""):
            items = []
            if ws_res.exists():
                items.append("workspace")
            if pf_res.exists():
                items.append("profiles")
            return sorted(items)
        if not (
            path.startswith("workspace/")
            or path == "workspace"
            or path.startswith("profiles/")
            or path == "profiles"
        ):
            path = "workspace/" + path
        base = (self.agent_root / path).resolve()
        if not base.is_relative_to(root_res):
            raise PermissionError("Path outside agent root")
        if base == root_res:
            items = []
            if ws_res.exists():
                items.append("workspace")
            if pf_res.exists():
                items.append("profiles")
            return sorted(items)
        if not (base.is_relative_to(ws_res) or base.is_relative_to(pf_res)):
            raise PermissionError("Only workspace/ and profiles/ can be listed")
        if not base.is_dir():
            raise PermissionError("Not a directory")
        items = [p.name for p in sorted(base.iterdir())]
        return items

    # --- Profile operations (for worker HTTP endpoints) ---

    def list_profile(self) -> list[str]:
        """List relative paths of all files under profiles/."""
        return self._list_under(self.profile_path)

    def read_profile(self, path: str) -> str | None:
        """Read a file under profiles/. Returns None if not found or path invalid."""
        return self._read_under(self.profile_path, path)

    def write_profile(self, path: str, content: str) -> bool:
        """Write a file under profiles/. Returns False if path invalid."""
        return self._write_under(self.profile_path, path, content)

    # --- Workspace operations (for worker HTTP endpoints) ---

    def list_workspace(self) -> list[str]:
        """List relative paths of all files under workspace/."""
        return self._list_under(self.workspace_path)

    def read_workspace(self, path: str) -> str | None:
        """Read a file under workspace/. Returns None if not found or path invalid."""
        return self._read_under(self.workspace_path, path)

    def write_workspace(self, path: str, content: str) -> bool:
        """Write a text file under workspace/. Returns False if path invalid."""
        return self._write_under(self.workspace_path, path, content)

    def upload_workspace(self, path: str, content: bytes) -> bool:
        """Write a binary file under workspace/. Returns False if path invalid."""
        return self._write_under(self.workspace_path, path, content)

    def create_folder_workspace(self, path: str) -> bool:
        """Create a folder under workspace/. Returns False if path invalid."""
        sanitized = self._sanitize_path(path, allow_empty=False)
        if sanitized is None:
            return False
        full = self._resolve_under(self.workspace_path, sanitized)
        if full is None:
            return False
        full.mkdir(parents=True, exist_ok=True)
        return True

    def delete_workspace(self, path: str) -> bool:
        """Delete a file or directory under workspace/. Returns False if path invalid or not found."""
        sanitized = self._sanitize_path(path, allow_empty=False)
        if sanitized is None:
            return False
        full = self._resolve_under(self.workspace_path, sanitized)
        if full is None or not full.exists():
            return False
        if full.is_dir():
            shutil.rmtree(full)
        else:
            full.unlink()
        return True

    def rename_workspace(self, old_path: str, new_name: str) -> bool:
        """Rename a file or directory under workspace/. Returns False if path invalid."""
        sanitized = self._sanitize_path(old_path, allow_empty=False)
        if sanitized is None:
            return False
        new_name = new_name.strip()
        if not new_name or "/" in new_name or ".." in new_name:
            return False
        full = self._resolve_under(self.workspace_path, sanitized)
        if full is None or not full.exists():
            return False
        new_full = full.parent / new_name
        if not new_full.is_relative_to(self.workspace_path.resolve()):
            return False
        if new_full.exists():
            return False
        full.rename(new_full)
        return True

    def move_workspace(self, src_path: str, dest_path: str) -> bool:
        """Move a file or directory under workspace/. Returns False if path invalid."""
        src_sanitized = self._sanitize_path(src_path, allow_empty=False)
        dest_sanitized = self._sanitize_path(dest_path, allow_empty=False)
        if src_sanitized is None or dest_sanitized is None:
            return False
        src_full = self._resolve_under(self.workspace_path, src_sanitized)
        dest_full = self._resolve_under(self.workspace_path, dest_sanitized)
        if src_full is None or dest_full is None:
            return False
        if not src_full.exists():
            return False
        if dest_full.exists():
            return False
        dest_full.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_full), str(dest_full))
        return True

    @property
    def crons_path(self) -> Path:
        """Path to crons/jobs.json under profiles (for CronService)."""
        return self._crons_path / "jobs.json"

    def _sanitize_path(self, path: str, allow_empty: bool = True) -> str | None:
        """Normalize path and validate. Returns None if invalid."""
        path = path.lstrip("/").replace("\\", "/")
        if ".." in path:
            return None
        if not allow_empty and not path:
            return None
        return path

    def _resolve_under(self, base: Path, path: str) -> Path | None:
        """Resolve path under base. Returns None if outside base."""
        full = (base / path).resolve()
        if not full.is_relative_to(base.resolve()):
            return None
        return full

    def _list_under(self, base: Path) -> list[str]:
        """List relative paths of all files under base."""
        if not base.exists():
            return []
        return sorted(
            str(p.relative_to(base)).replace("\\", "/") for p in base.rglob("*") if p.is_file()
        )

    def list_dir_tree(self, root: str = "workspace", max_depth: int = 6) -> str:
        """Build a hierarchical tree view of workspace or profiles.

        Returns a formatted tree string for smart workspace overview.
        Use this instead of repeatedly calling list_dir when exploring structure.
        """
        if root == "profiles":
            paths = self._list_under(self.profile_path)
            prefix = "profiles"
        else:
            paths = self._list_under(self.workspace_path)
            prefix = "workspace"

        if not paths:
            return f"{prefix}/\n  (empty)"

        # Build tree: { "a": {"b": {"c": None} } } where None = file
        tree: dict = {}

        def ensure_path(d: dict, parts: list[str], is_file: bool) -> None:
            for i, part in enumerate(parts):
                is_last = i == len(parts) - 1
                if part not in d:
                    d[part] = {} if not is_last or not is_file else None
                if is_last and is_file:
                    d[part] = None
                    return
                if d[part] is None:
                    d[part] = {}
                d = d[part]

        for p in paths:
            parts = p.split("/")
            if len(parts) > max_depth:
                parts = parts[: max_depth - 1] + ["..."]
            ensure_path(tree, parts, True)

        def format_tree(d: dict, indent: str = "", is_last_sibling: bool = True) -> list[str]:
            lines: list[str] = []
            items = sorted(d.items(), key=lambda x: (x[1] is None, x[0].lower()))  # dirs first
            for i, (name, child) in enumerate(items):
                last = i == len(items) - 1
                branch = "└── " if last else "├── "
                lines.append(
                    f"{indent}{branch}{name}/" if child is not None else f"{indent}{branch}{name}"
                )
                if child is not None and isinstance(child, dict):
                    ext = "    " if last else "│   "
                    lines.extend(format_tree(child, indent + ext, last))
            return lines

        lines = [f"{prefix}/"] + format_tree(tree)
        return "\n".join(lines)

    def _read_under(self, base: Path, path: str) -> str | None:
        """Read file under base. Returns None if not found or invalid."""
        sanitized = self._sanitize_path(path)
        if sanitized is None:
            return None
        full = self._resolve_under(base, sanitized)
        if full is None or not full.is_file():
            return None
        return full.read_text(encoding="utf-8", errors="replace")

    def _write_under(self, base: Path, path: str, content: str | bytes) -> bool:
        """Write file under base. Returns False if path invalid."""
        sanitized = self._sanitize_path(path)
        if sanitized is None:
            return False
        full = self._resolve_under(base, sanitized)
        if full is None:
            return False
        full.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            full.write_text(content, encoding="utf-8")
        else:
            full.write_bytes(content)
        return True
