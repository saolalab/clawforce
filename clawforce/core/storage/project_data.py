"""Project data directory layout under admin storage.

Layout::

    {storage_root}/admin/project_data/
    └── {project_id}/
        └── (arbitrary files for that project)

Use project_data_prefix(project_id) to get the storage path prefix for a project.
Per-project directories are created on first write; the project_data root is
created when the storage backend is initialized.

Relationship to plans: A plan can be used as a project scope by using plan_id
as project_id (e.g. project_data/{plan_id}/ for plan-specific files). Plan
artifact metadata lives in SQLite (plan_artifacts table); project_data is for
binary artifact files and custom layout per project.
"""

from pathlib import Path

from clawlib.storage import LocalStorage, StorageBackend, get_storage_root

PROJECT_DATA_DIR = "admin/project_data"


def _sanitize_project_id(project_id: str) -> str:
    """Ensure project_id is a single path segment (no slashes or parent refs)."""
    if not project_id or ".." in project_id or "/" in project_id or "\\" in project_id:
        raise ValueError(f"Invalid project_id: {project_id!r}")
    return project_id


def project_data_prefix(project_id: str) -> str:
    """Return the storage path prefix for a project's data directory.

    Use with storage read/write/list_dir, e.g.:
        prefix = project_data_prefix("my-project")
        await storage.write(f"{prefix}/file.txt", b"content")
    """
    pid = _sanitize_project_id(project_id)
    return f"{PROJECT_DATA_DIR}/{pid}"


def ensure_project_data_dir(storage: StorageBackend, project_id: str) -> None:
    """Ensure the project's data directory exists under project_data.

    Idempotent; safe to call on every access. Uses a .gitkeep file so the
    directory is persisted even when empty.
    """
    prefix = project_data_prefix(project_id)
    try:
        storage.write_sync(f"{prefix}/.gitkeep", b"")
    except Exception:
        pass


def get_project_data_path_on_disk(storage: StorageBackend, project_id: str) -> Path | None:
    """Return the filesystem path for a project's data dir, or None if not local storage.

    Useful when passing a directory to external tools or workers that need a local path.
    """
    if not isinstance(storage, LocalStorage):
        return None
    root = get_storage_root(storage)
    pid = _sanitize_project_id(project_id)
    return root / PROJECT_DATA_DIR / pid
