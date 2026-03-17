"""Plan workspace filesystem storage.

Layout under project_data/{plan_id}/:
    workspace/   - user files for the plan (similar to agent workspace)

This provides a full filesystem for each plan where users can organize
files, create folders, and manage documents related to the plan.
"""

import asyncio
import shutil

from clawforce.core.path_utils import validate_path
from clawforce.core.storage import (
    StorageBackend,
    ensure_project_data_dir,
    get_project_data_path_on_disk,
    get_storage_backend,
    project_data_prefix,
)


class PlanWorkspaceStore:
    """Filesystem operations for plan workspaces."""

    def __init__(self, storage: StorageBackend | None = None) -> None:
        self._storage = storage or get_storage_backend()

    def _workspace_prefix(self, plan_id: str) -> str:
        """Return the storage path prefix for a plan's workspace."""
        return f"{project_data_prefix(plan_id)}/workspace"

    def _ensure_workspace(self, plan_id: str) -> None:
        """Ensure the workspace directory exists."""
        ensure_project_data_dir(self._storage, plan_id)
        prefix = self._workspace_prefix(plan_id)
        try:
            self._storage.write_sync(f"{prefix}/.gitkeep", b"")
        except Exception:
            pass

    def list_files(self, plan_id: str) -> list[str]:
        """List all files in the plan workspace recursively."""
        self._ensure_workspace(plan_id)
        prefix = self._workspace_prefix(plan_id)
        disk_path = get_project_data_path_on_disk(self._storage, plan_id)

        if disk_path:
            workspace_path = disk_path / "workspace"
            if not workspace_path.exists():
                return []
            files = []
            for p in workspace_path.rglob("*"):
                if p.is_file() and p.name != ".gitkeep":
                    rel = p.relative_to(workspace_path)
                    files.append(str(rel).replace("\\", "/"))
            return sorted(files)

        # Fallback for non-local storage (async would be better but keeping sync for simplicity)
        try:
            loop = asyncio.get_event_loop()
            files = loop.run_until_complete(self._storage.list_dir(prefix))
        except RuntimeError:
            files = asyncio.run(self._storage.list_dir(prefix))
        return [f for f in files if f != ".gitkeep"]

    def read_file(self, plan_id: str, path: str) -> str | None:
        """Read a text file from the workspace. Returns None if not found."""
        path = validate_path(path)
        prefix = self._workspace_prefix(plan_id)
        try:
            data = self._storage.read_sync(f"{prefix}/{path}")
            return data.decode("utf-8")
        except (FileNotFoundError, UnicodeDecodeError):
            return None

    def read_file_binary(self, plan_id: str, path: str) -> bytes | None:
        """Read a binary file from the workspace. Returns None if not found."""
        path = validate_path(path)
        prefix = self._workspace_prefix(plan_id)
        try:
            return self._storage.read_sync(f"{prefix}/{path}")
        except FileNotFoundError:
            return None

    def write_file(self, plan_id: str, path: str, content: str) -> bool:
        """Write a text file to the workspace."""
        path = validate_path(path)
        self._ensure_workspace(plan_id)
        prefix = self._workspace_prefix(plan_id)
        try:
            self._storage.write_sync(f"{prefix}/{path}", content.encode("utf-8"))
            return True
        except Exception:
            return False

    def write_file_binary(self, plan_id: str, path: str, data: bytes) -> bool:
        """Write a binary file to the workspace."""
        path = validate_path(path)
        self._ensure_workspace(plan_id)
        prefix = self._workspace_prefix(plan_id)
        try:
            self._storage.write_sync(f"{prefix}/{path}", data)
            return True
        except Exception:
            return False

    def delete_file(self, plan_id: str, path: str) -> bool:
        """Delete a file or directory from the workspace."""
        path = validate_path(path)
        disk_path = get_project_data_path_on_disk(self._storage, plan_id)

        if disk_path:
            full_path = disk_path / "workspace" / path
            if not full_path.exists():
                return False
            try:
                if full_path.is_file():
                    full_path.unlink()
                elif full_path.is_dir():
                    shutil.rmtree(full_path)
                return True
            except Exception:
                return False

        # Fallback: just try to delete from storage
        prefix = self._workspace_prefix(plan_id)
        try:
            self._storage.delete_sync(f"{prefix}/{path}")
            return True
        except Exception:
            return False

    def rename_file(self, plan_id: str, path: str, new_name: str) -> bool:
        """Rename a file or directory in the workspace."""
        path = validate_path(path)
        if "/" in new_name or ".." in new_name:
            return False

        disk_path = get_project_data_path_on_disk(self._storage, plan_id)
        if not disk_path:
            return False

        full_path = disk_path / "workspace" / path
        if not full_path.exists():
            return False

        parent = full_path.parent
        new_path = parent / new_name
        if new_path.exists():
            return False

        try:
            full_path.rename(new_path)
            return True
        except Exception:
            return False

    def move_file(self, plan_id: str, src_path: str, dest_path: str) -> bool:
        """Move a file or directory within the workspace."""
        src_path = validate_path(src_path)
        dest_path = validate_path(dest_path)

        disk_path = get_project_data_path_on_disk(self._storage, plan_id)
        if not disk_path:
            return False

        workspace = disk_path / "workspace"
        src_full = workspace / src_path
        dest_full = workspace / dest_path

        if not src_full.exists():
            return False
        if dest_full.exists():
            return False

        try:
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_full), str(dest_full))
            return True
        except Exception:
            return False

    def create_folder(self, plan_id: str, path: str) -> bool:
        """Create a folder in the workspace."""
        path = validate_path(path)
        disk_path = get_project_data_path_on_disk(self._storage, plan_id)

        if disk_path:
            folder_path = disk_path / "workspace" / path
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                return True
            except Exception:
                return False

        # For non-local storage, create a .gitkeep file
        prefix = self._workspace_prefix(plan_id)
        try:
            self._storage.write_sync(f"{prefix}/{path}/.gitkeep", b"")
            return True
        except Exception:
            return False

    def delete_all_for_plan(self, plan_id: str) -> None:
        """Delete all workspace files for a plan. Called when plan is deleted."""
        disk_path = get_project_data_path_on_disk(self._storage, plan_id)
        if disk_path:
            workspace = disk_path / "workspace"
            if workspace.exists():
                try:
                    shutil.rmtree(workspace)
                except Exception:
                    pass
