"""Plan artifact storage (admin-side). Metadata in SQLite; binary files in project_data/.

Design:
- Artifact metadata (id, plan_id, task_id, name, content_type, content, file_path, size, created_at)
  is stored in the plan_artifacts table.
- Text artifacts keep content inline in the content column.
- File artifacts store binary data under project_data/{plan_id}/artifacts/{artifact_id}/{filename}
  and set file_path in the row.
- When a plan is deleted, rows are CASCADE deleted; delete_all_for_plan() cleans up project_data.
"""

import uuid
from datetime import datetime, timezone

from clawforce.core.database import Database
from clawforce.core.storage import StorageBackend, get_storage_backend
from clawforce.core.storage.project_data import ensure_project_data_dir, project_data_prefix


def _row_to_artifact(row) -> dict:
    """Convert SQLite row to artifact dict for API response."""
    d = dict(row)
    return {
        "id": d["id"],
        "task_id": d.get("task_id") or "",
        "name": d.get("name") or "",
        "content_type": d.get("content_type") or "text/plain",
        "content": d.get("content") or "",
        "file_path": d.get("file_path") or "",
        "size": d.get("size") or 0,
        "created_at": d["created_at"],
    }


class PlanArtifactStore:
    """Store and list plan artifacts. Metadata in SQLite; binary files in project_data/."""

    def __init__(
        self,
        db: Database | None = None,
        storage: StorageBackend | None = None,
    ) -> None:
        from clawforce.core.database import get_database

        self._db = db or get_database()
        self._storage = storage or get_storage_backend()

    def add(
        self,
        plan_id: str,
        name: str,
        content: str,
        task_id: str = "",
        content_type: str = "text/plain",
    ) -> dict:
        """Store a text artifact as a file on disk; SQLite holds only metadata."""
        artifact_id = str(uuid.uuid4())
        data = content.encode("utf-8")
        size = len(data)
        ensure_project_data_dir(self._storage, plan_id)
        prefix = project_data_prefix(plan_id)
        file_path = f"{prefix}/artifacts/{artifact_id}/{name}"
        self._storage.write_sync(file_path, data)
        created_at = datetime.now(timezone.utc).isoformat()
        with self._db.connection() as conn:
            conn.execute(
                """INSERT INTO plan_artifacts (id, plan_id, task_id, name, content_type, content, file_path, size, created_at)
                   VALUES (?, ?, ?, ?, ?, '', ?, ?, ?)""",
                (artifact_id, plan_id, task_id, name, content_type, file_path, size, created_at),
            )
        return {
            "id": artifact_id,
            "task_id": task_id,
            "name": name,
            "content_type": content_type,
            "content": "",
            "file_path": file_path,
            "size": size,
            "created_at": created_at,
        }

    def add_file(
        self,
        plan_id: str,
        name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        task_id: str = "",
    ) -> dict:
        """Store a binary file under project_data and add metadata row."""
        artifact_id = str(uuid.uuid4())
        ensure_project_data_dir(self._storage, plan_id)
        prefix = project_data_prefix(plan_id)
        file_path = f"{prefix}/artifacts/{artifact_id}/{name}"
        self._storage.write_sync(file_path, data)

        size = len(data)
        created_at = datetime.now(timezone.utc).isoformat()
        with self._db.connection() as conn:
            conn.execute(
                """INSERT INTO plan_artifacts (id, plan_id, task_id, name, content_type, content, file_path, size, created_at)
                   VALUES (?, ?, ?, ?, ?, '', ?, ?, ?)""",
                (artifact_id, plan_id, task_id, name, content_type, file_path, size, created_at),
            )
        return {
            "id": artifact_id,
            "task_id": task_id,
            "name": name,
            "content_type": content_type,
            "content": "",
            "file_path": file_path,
            "size": size,
            "created_at": created_at,
        }

    def read_file(self, plan_id: str, artifact_id: str) -> tuple[dict, bytes] | None:
        """Return (metadata, bytes) for a file artifact, or None if not found."""
        artifact = self.get_artifact(plan_id, artifact_id)
        if not artifact:
            return None
        file_path = artifact.get("file_path", "")
        if not file_path:
            return artifact, artifact.get("content", "").encode("utf-8")
        try:
            data = self._storage.read_sync(file_path)
        except FileNotFoundError:
            return None
        return artifact, data

    def delete_artifact(self, plan_id: str, artifact_id: str) -> bool:
        """Delete a single artifact (row + file if present). Returns True if found."""
        artifact = self.get_artifact(plan_id, artifact_id)
        if not artifact:
            return False
        file_path = artifact.get("file_path", "")
        if file_path:
            try:
                self._storage.delete_sync(file_path)
            except (FileNotFoundError, ValueError):
                pass
        with self._db.connection() as conn:
            cursor = conn.execute("DELETE FROM plan_artifacts WHERE id = ?", (artifact_id,))
            return cursor.rowcount > 0

    def list_artifacts(self, plan_id: str, task_id: str | None = None) -> list[dict]:
        with self._db.connection() as conn:
            if task_id:
                rows = conn.execute(
                    "SELECT * FROM plan_artifacts WHERE plan_id = ? AND task_id = ? ORDER BY created_at",
                    (plan_id, task_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM plan_artifacts WHERE plan_id = ? ORDER BY created_at",
                    (plan_id,),
                ).fetchall()
            return [_row_to_artifact(r) for r in rows]

    def get_artifact(self, plan_id: str, artifact_id: str) -> dict | None:
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM plan_artifacts WHERE id = ? AND plan_id = ?",
                (artifact_id, plan_id),
            ).fetchone()
            return _row_to_artifact(row) if row else None

    def rename_artifact(self, plan_id: str, artifact_id: str, new_name: str) -> dict | None:
        """Rename an artifact. For file artifacts, also renames the file on disk."""
        if "/" in new_name or ".." in new_name:
            return None
        artifact = self.get_artifact(plan_id, artifact_id)
        if not artifact:
            return None

        old_file_path = artifact.get("file_path", "")
        new_file_path = ""

        if old_file_path:
            prefix = project_data_prefix(plan_id)
            new_file_path = f"{prefix}/artifacts/{artifact_id}/{new_name}"
            try:
                data = self._storage.read_sync(old_file_path)
                self._storage.write_sync(new_file_path, data)
                self._storage.delete_sync(old_file_path)
            except (FileNotFoundError, ValueError):
                return None

        with self._db.connection() as conn:
            conn.execute(
                """UPDATE plan_artifacts SET name = ?, file_path = ?
                   WHERE id = ? AND plan_id = ?""",
                (new_name, new_file_path or old_file_path, artifact_id, plan_id),
            )

        artifact["name"] = new_name
        if new_file_path:
            artifact["file_path"] = new_file_path
        return artifact

    def move_artifact(self, plan_id: str, artifact_id: str, new_task_id: str) -> dict | None:
        """Move an artifact to a different task (or no task if empty string)."""
        artifact = self.get_artifact(plan_id, artifact_id)
        if not artifact:
            return None

        with self._db.connection() as conn:
            conn.execute(
                """UPDATE plan_artifacts SET task_id = ? WHERE id = ? AND plan_id = ?""",
                (new_task_id, artifact_id, plan_id),
            )

        artifact["task_id"] = new_task_id
        return artifact

    def delete_all_for_plan(self, plan_id: str) -> None:
        """Remove all artifact rows for this plan and clean project_data. Idempotent."""
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT id, file_path FROM plan_artifacts WHERE plan_id = ?",
                (plan_id,),
            ).fetchall()
            for r in rows:
                fp = r.get("file_path", "")
                if fp:
                    try:
                        self._storage.delete_sync(fp)
                    except (FileNotFoundError, ValueError):
                        pass
            conn.execute("DELETE FROM plan_artifacts WHERE plan_id = ?", (plan_id,))
