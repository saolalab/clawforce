"""Local filesystem storage backend. Default root: ADMIN_STORAGE_ROOT or ~/.clawbot."""

import contextlib
import os
import threading
from collections.abc import Generator
from pathlib import Path

from clawlib.storage.base import StorageBackend


def _default_storage_root() -> Path:
    return Path.home() / ".clawbot"


class LocalStorage(StorageBackend):
    """Storage backend using local filesystem under ADMIN_STORAGE_ROOT or ~/.clawbot."""

    _file_locks: dict[str, threading.Lock] = {}
    _meta_lock = threading.Lock()

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root).expanduser() if root else _default_storage_root()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "admin" / "project_data").mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        p = (self.root / path).resolve()
        if not p.is_relative_to(self.root.resolve()):
            raise ValueError(f"Path escape not allowed: {path}")
        return p

    async def read(self, path: str) -> bytes:
        full = self._resolve(path)
        if not full.exists():
            raise FileNotFoundError(path)
        return full.read_bytes()

    async def write(self, path: str, data: bytes) -> None:
        full = self._resolve(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)

    async def delete(self, path: str) -> None:
        full = self._resolve(path)
        if full.exists():
            if full.is_file():
                full.unlink()
            elif full.is_dir() and not any(full.iterdir()):
                full.rmdir()

    async def list_dir(self, prefix: str) -> list[str]:
        full = self._resolve(prefix)
        if not full.exists() or not full.is_dir():
            return []
        out: list[str] = []
        for p in full.rglob("*"):
            if p.is_file():
                rel = p.relative_to(full)
                out.append(str(rel).replace("\\", "/"))
        return sorted(out)

    async def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def read_sync(self, path: str) -> bytes:
        full = self._resolve(path)
        if not full.exists():
            raise FileNotFoundError(path)
        return full.read_bytes()

    def write_sync(self, path: str, data: bytes) -> None:
        full = self._resolve(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)

    def delete_sync(self, path: str) -> None:
        full = self._resolve(path)
        if full.exists():
            if full.is_file():
                full.unlink()
            elif full.is_dir() and not any(full.iterdir()):
                full.rmdir()

    def _get_file_lock(self, path: str) -> threading.Lock:
        with self._meta_lock:
            if path not in self._file_locks:
                self._file_locks[path] = threading.Lock()
            return self._file_locks[path]

    @contextlib.contextmanager
    def lock(self, path: str) -> Generator[None, None, None]:
        """Hold per-file lock for the duration of a read-modify-write cycle."""
        lk = self._get_file_lock(path)
        lk.acquire()
        try:
            yield
        finally:
            lk.release()


def get_storage_root(storage: StorageBackend) -> Path:
    """Return filesystem root for local storage; used for per-agent config and data paths."""
    if isinstance(storage, LocalStorage):
        return Path(storage.root)
    return _default_storage_root()


def get_storage_backend() -> StorageBackend:
    """Return storage backend from ADMIN_STORAGE_BACKEND (default: local)."""
    kind = (os.environ.get("ADMIN_STORAGE_BACKEND") or "local").lower()
    if kind == "local":
        root = os.environ.get("ADMIN_STORAGE_ROOT") or str(_default_storage_root())
        return LocalStorage(root=root)
    if kind == "s3":
        from clawlib.storage.s3 import S3Storage

        bucket = os.environ.get("S3_BUCKET", "")
        prefix = os.environ.get("S3_PREFIX", "")
        endpoint = os.environ.get("S3_ENDPOINT")
        region = os.environ.get("S3_REGION", "us-east-1")
        if not bucket:
            raise ValueError("S3_BUCKET is required when ADMIN_STORAGE_BACKEND=s3")
        return S3Storage(bucket=bucket, prefix=prefix, endpoint_url=endpoint, region_name=region)
    raise ValueError(f"Unknown ADMIN_STORAGE_BACKEND: {kind}")
