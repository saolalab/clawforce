"""Storage backend ABC. Shared by clawforce and clawbot."""

import contextlib
from abc import ABC, abstractmethod
from collections.abc import Generator


class StorageBackend(ABC):
    """Abstract base for persistent storage (teams, workspaces, sessions)."""

    @abstractmethod
    async def read(self, path: str) -> bytes: ...

    @abstractmethod
    async def write(self, path: str, data: bytes) -> None: ...

    @abstractmethod
    async def delete(self, path: str) -> None: ...

    @abstractmethod
    async def list_dir(self, prefix: str) -> list[str]: ...

    @abstractmethod
    async def exists(self, path: str) -> bool: ...

    def read_sync(self, path: str) -> bytes:
        """Synchronous read. Override in backends that do real I/O (e.g. LocalStorage)."""
        raise NotImplementedError("read_sync not implemented for this backend")

    def write_sync(self, path: str, data: bytes) -> None:
        """Synchronous write. Override in backends that do real I/O (e.g. LocalStorage)."""
        raise NotImplementedError("write_sync not implemented for this backend")

    def delete_sync(self, path: str) -> None:
        """Synchronous delete (file or empty dir). Override in backends that do real I/O."""
        raise NotImplementedError("delete_sync not implemented for this backend")

    @contextlib.contextmanager
    def lock(self, path: str) -> Generator[None, None, None]:
        """Hold an exclusive lock for *path* across a read-modify-write cycle."""
        yield
