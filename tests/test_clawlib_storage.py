"""Tests for clawlib.storage module."""

from pathlib import Path

import pytest

from clawlib.storage.base import StorageBackend
from clawlib.storage.local import LocalStorage, get_storage_backend, get_storage_root


class TestStorageBackendABC:
    """Tests for StorageBackend abstract base class."""

    def test_storage_backend_is_abstract(self):
        """StorageBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            StorageBackend()

    def test_sync_methods_raise_not_implemented(self):
        """Default sync methods should raise NotImplementedError."""

        class MinimalStorage(StorageBackend):
            async def read(self, path: str) -> bytes:
                return b""

            async def write(self, path: str, data: bytes) -> None:
                pass

            async def delete(self, path: str) -> None:
                pass

            async def list_dir(self, prefix: str) -> list[str]:
                return []

            async def exists(self, path: str) -> bool:
                return False

        storage = MinimalStorage()
        with pytest.raises(NotImplementedError):
            storage.read_sync("test")
        with pytest.raises(NotImplementedError):
            storage.write_sync("test", b"data")
        with pytest.raises(NotImplementedError):
            storage.delete_sync("test")


class TestLocalStorage:
    """Tests for LocalStorage implementation."""

    def test_init_creates_directories(self, tmp_storage: Path):
        """LocalStorage should create root and admin/project_data directories."""
        storage = LocalStorage(root=tmp_storage)
        assert storage.root == tmp_storage
        assert (tmp_storage / "admin" / "project_data").exists()

    def test_init_default_root(self, monkeypatch):
        """LocalStorage should use ~/.clawbot as default root."""
        monkeypatch.setattr(
            "clawlib.storage.local._default_storage_root", lambda: Path("/tmp/test_default")
        )
        storage = LocalStorage(root="/tmp/test_default")
        assert storage.root == Path("/tmp/test_default")

    @pytest.mark.asyncio
    async def test_write_and_read(self, tmp_storage: Path):
        """LocalStorage should write and read files correctly."""
        storage = LocalStorage(root=tmp_storage)
        await storage.write("test.txt", b"hello world")
        content = await storage.read("test.txt")
        assert content == b"hello world"

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self, tmp_storage: Path):
        """LocalStorage should create parent directories on write."""
        storage = LocalStorage(root=tmp_storage)
        await storage.write("subdir/nested/file.txt", b"nested content")
        content = await storage.read("subdir/nested/file.txt")
        assert content == b"nested content"

    @pytest.mark.asyncio
    async def test_read_nonexistent_raises(self, tmp_storage: Path):
        """LocalStorage should raise FileNotFoundError for missing files."""
        storage = LocalStorage(root=tmp_storage)
        with pytest.raises(FileNotFoundError):
            await storage.read("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_delete_file(self, tmp_storage: Path):
        """LocalStorage should delete files correctly."""
        storage = LocalStorage(root=tmp_storage)
        await storage.write("to_delete.txt", b"delete me")
        assert await storage.exists("to_delete.txt")
        await storage.delete("to_delete.txt")
        assert not await storage.exists("to_delete.txt")

    @pytest.mark.asyncio
    async def test_delete_empty_dir(self, tmp_storage: Path):
        """LocalStorage should delete empty directories."""
        storage = LocalStorage(root=tmp_storage)
        empty_dir = tmp_storage / "empty_dir"
        empty_dir.mkdir()
        assert empty_dir.exists()
        await storage.delete("empty_dir")
        assert not empty_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_noop(self, tmp_storage: Path):
        """Deleting a nonexistent path should not raise."""
        storage = LocalStorage(root=tmp_storage)
        await storage.delete("does_not_exist.txt")

    @pytest.mark.asyncio
    async def test_exists(self, tmp_storage: Path):
        """LocalStorage.exists should return correct values."""
        storage = LocalStorage(root=tmp_storage)
        assert not await storage.exists("test_exists.txt")
        await storage.write("test_exists.txt", b"exists")
        assert await storage.exists("test_exists.txt")

    @pytest.mark.asyncio
    async def test_list_dir(self, tmp_storage: Path):
        """LocalStorage.list_dir should return all files recursively."""
        storage = LocalStorage(root=tmp_storage)
        await storage.write("dir/file1.txt", b"1")
        await storage.write("dir/file2.txt", b"2")
        await storage.write("dir/sub/file3.txt", b"3")

        files = await storage.list_dir("dir")
        assert sorted(files) == ["file1.txt", "file2.txt", "sub/file3.txt"]

    @pytest.mark.asyncio
    async def test_list_dir_empty(self, tmp_storage: Path):
        """LocalStorage.list_dir should return empty list for empty/nonexistent dirs."""
        storage = LocalStorage(root=tmp_storage)
        assert await storage.list_dir("nonexistent") == []

    def test_sync_read_write(self, tmp_storage: Path):
        """LocalStorage sync methods should work correctly."""
        storage = LocalStorage(root=tmp_storage)
        storage.write_sync("sync_test.txt", b"sync content")
        content = storage.read_sync("sync_test.txt")
        assert content == b"sync content"

    def test_sync_read_nonexistent_raises(self, tmp_storage: Path):
        """LocalStorage.read_sync should raise for missing files."""
        storage = LocalStorage(root=tmp_storage)
        with pytest.raises(FileNotFoundError):
            storage.read_sync("missing.txt")

    def test_sync_delete(self, tmp_storage: Path):
        """LocalStorage.delete_sync should work correctly."""
        storage = LocalStorage(root=tmp_storage)
        storage.write_sync("to_delete_sync.txt", b"delete")
        storage.delete_sync("to_delete_sync.txt")
        assert not (tmp_storage / "to_delete_sync.txt").exists()

    def test_path_escape_protection(self, tmp_storage: Path):
        """LocalStorage should prevent path escape attacks."""
        storage = LocalStorage(root=tmp_storage)
        with pytest.raises(ValueError, match="Path escape not allowed"):
            storage._resolve("../../../etc/passwd")

    def test_lock_context_manager(self, tmp_storage: Path):
        """LocalStorage.lock should provide thread-safe access."""
        storage = LocalStorage(root=tmp_storage)
        with storage.lock("test_lock"):
            storage.write_sync("locked_file.txt", b"locked write")
        content = storage.read_sync("locked_file.txt")
        assert content == b"locked write"

    def test_lock_reentrant_for_different_paths(self, tmp_storage: Path):
        """Different paths should have independent locks."""
        storage = LocalStorage(root=tmp_storage)
        with storage.lock("path1"):
            with storage.lock("path2"):
                pass


class TestGetStorageRoot:
    """Tests for get_storage_root helper."""

    def test_get_storage_root_local(self, tmp_storage: Path):
        """get_storage_root should return root for LocalStorage."""
        storage = LocalStorage(root=tmp_storage)
        assert get_storage_root(storage) == tmp_storage

    def test_get_storage_root_non_local(self):
        """get_storage_root should return default for non-local storage."""

        class FakeStorage(StorageBackend):
            async def read(self, path: str) -> bytes:
                return b""

            async def write(self, path: str, data: bytes) -> None:
                pass

            async def delete(self, path: str) -> None:
                pass

            async def list_dir(self, prefix: str) -> list[str]:
                return []

            async def exists(self, path: str) -> bool:
                return False

        storage = FakeStorage()
        root = get_storage_root(storage)
        assert root == Path.home() / ".clawbot"


class TestGetStorageBackend:
    """Tests for get_storage_backend factory."""

    def test_default_local_backend(self, monkeypatch, tmp_storage: Path):
        """Default storage backend should be local."""
        monkeypatch.delenv("ADMIN_STORAGE_BACKEND", raising=False)
        monkeypatch.setenv("ADMIN_STORAGE_ROOT", str(tmp_storage))
        storage = get_storage_backend()
        assert isinstance(storage, LocalStorage)
        assert storage.root == tmp_storage

    def test_explicit_local_backend(self, monkeypatch, tmp_storage: Path):
        """Explicit local backend should work."""
        monkeypatch.setenv("ADMIN_STORAGE_BACKEND", "local")
        monkeypatch.setenv("ADMIN_STORAGE_ROOT", str(tmp_storage))
        storage = get_storage_backend()
        assert isinstance(storage, LocalStorage)

    def test_unknown_backend_raises(self, monkeypatch):
        """Unknown storage backend should raise ValueError."""
        monkeypatch.setenv("ADMIN_STORAGE_BACKEND", "unknown")
        with pytest.raises(ValueError, match="Unknown ADMIN_STORAGE_BACKEND"):
            get_storage_backend()

    def test_s3_backend_requires_bucket(self, monkeypatch):
        """S3 backend should require S3_BUCKET."""
        monkeypatch.setenv("ADMIN_STORAGE_BACKEND", "s3")
        monkeypatch.delenv("S3_BUCKET", raising=False)
        with pytest.raises(ValueError, match="S3_BUCKET is required"):
            get_storage_backend()
