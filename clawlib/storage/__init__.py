"""Storage backends: local filesystem and S3-compatible."""

from clawlib.storage.base import StorageBackend
from clawlib.storage.local import (
    LocalStorage,
    get_storage_backend,
    get_storage_root,
)

__all__ = [
    "StorageBackend",
    "LocalStorage",
    "get_storage_backend",
    "get_storage_root",
]
