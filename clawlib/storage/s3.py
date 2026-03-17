"""S3-compatible storage backend (AWS S3, MinIO, R2). Requires clawlib[s3] (boto3)."""

import asyncio
import os

from clawlib.storage.base import StorageBackend


def _norm_key(path: str) -> str:
    return path.replace("\\", "/").strip("/")


class S3Storage(StorageBackend):
    """S3-compatible storage backend. Paths are object keys under prefix."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        endpoint_url: str | None = None,
        region_name: str = "us-east-1",
    ) -> None:
        self.bucket = bucket
        self.prefix = _norm_key(prefix) if prefix else ""
        self._endpoint_url = endpoint_url or os.environ.get("S3_ENDPOINT")
        self._region_name = region_name or os.environ.get("S3_REGION", "us-east-1")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as e:
                raise ImportError(
                    "S3 storage requires boto3. Install with: pip install clawlib[s3]"
                ) from e
            kw: dict = {"region_name": self._region_name}
            if self._endpoint_url:
                kw["endpoint_url"] = self._endpoint_url
            self._client = boto3.client("s3", config=Config(signature_version="s3v4"), **kw)
        return self._client

    def _key(self, path: str) -> str:
        if ".." in path or path.startswith("/"):
            raise ValueError(f"Path escape not allowed: {path}")
        k = _norm_key(path)
        return f"{self.prefix}/{k}" if self.prefix else k

    def _read_sync(self, path: str) -> bytes:
        key = self._key(path)
        resp = self._get_client().get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def _write_sync(self, path: str, data: bytes) -> None:
        key = self._key(path)
        self._get_client().put_object(Bucket=self.bucket, Key=key, Body=data)

    def _delete_sync(self, path: str) -> None:
        key = self._key(path)
        self._get_client().delete_object(Bucket=self.bucket, Key=key)

    def _list_dir_sync(self, prefix: str) -> list[str]:
        key_prefix = self._key(prefix)
        if not key_prefix.endswith("/"):
            key_prefix += "/"
        paginator = self._get_client().get_paginator("list_objects_v2")
        out: list[str] = []
        prefix_len = len(key_prefix)
        for page in paginator.paginate(Bucket=self.bucket, Prefix=key_prefix):
            for obj in page.get("Contents") or []:
                k = obj["Key"]
                if k.endswith("/"):
                    continue
                rel = k[prefix_len:].replace("\\", "/")
                out.append(rel)
        return sorted(out)

    def _exists_sync(self, path: str) -> bool:
        key = self._key(path)
        try:
            self._get_client().head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    async def read(self, path: str) -> bytes:
        return await asyncio.to_thread(self._read_sync, path)

    async def write(self, path: str, data: bytes) -> None:
        await asyncio.to_thread(self._write_sync, path, data)

    async def delete(self, path: str) -> None:
        await asyncio.to_thread(self._delete_sync, path)

    async def list_dir(self, prefix: str) -> list[str]:
        return await asyncio.to_thread(self._list_dir_sync, prefix)

    async def exists(self, path: str) -> bool:
        return await asyncio.to_thread(self._exists_sync, path)

    def read_sync(self, path: str) -> bytes:
        return self._read_sync(path)

    def write_sync(self, path: str, data: bytes) -> None:
        self._write_sync(path, data)

    def delete_sync(self, path: str) -> None:
        self._delete_sync(path)
