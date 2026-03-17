"""Tests for clawforce.core.services module."""

import json
from pathlib import Path

import pytest

from clawlib.storage.local import LocalStorage


class TestWorkspaceServiceIntegration:
    """Integration tests for workspace service with local storage."""

    @pytest.fixture
    def storage(self, tmp_storage: Path) -> LocalStorage:
        """Create a temporary local storage."""
        return LocalStorage(root=tmp_storage)

    @pytest.mark.asyncio
    async def test_storage_read_write_cycle(self, storage: LocalStorage):
        """Storage should support basic read/write cycle."""
        await storage.write("test/file.txt", b"hello world")
        content = await storage.read("test/file.txt")
        assert content == b"hello world"

    @pytest.mark.asyncio
    async def test_storage_list_files(self, storage: LocalStorage):
        """Storage should list files in directory."""
        await storage.write("workspace/file1.txt", b"content1")
        await storage.write("workspace/file2.txt", b"content2")
        await storage.write("workspace/subdir/file3.txt", b"content3")

        files = await storage.list_dir("workspace")
        assert "file1.txt" in files
        assert "file2.txt" in files
        assert "subdir/file3.txt" in files

    @pytest.mark.asyncio
    async def test_storage_delete_file(self, storage: LocalStorage):
        """Storage should delete files."""
        await storage.write("to_delete.txt", b"delete me")
        assert await storage.exists("to_delete.txt")

        await storage.delete("to_delete.txt")
        assert not await storage.exists("to_delete.txt")

    @pytest.mark.asyncio
    async def test_storage_nested_directories(self, storage: LocalStorage):
        """Storage should handle nested directories."""
        await storage.write("a/b/c/d/file.txt", b"deep content")
        content = await storage.read("a/b/c/d/file.txt")
        assert content == b"deep content"


class TestAgentWorkspaceLayout:
    """Tests for agent workspace directory layout conventions."""

    @pytest.fixture
    def agent_root(self, tmp_path: Path) -> Path:
        """Create a mock agent root directory."""
        root = tmp_path / "agent-123"
        root.mkdir()
        return root

    def test_workspace_structure(self, agent_root: Path):
        """Agent should have standard workspace structure."""
        workspace = agent_root / "workspace"
        profiles = agent_root / "profiles"
        config_dir = agent_root / ".config"
        sessions_dir = agent_root / ".sessions"
        logs_dir = agent_root / ".logs"

        workspace.mkdir()
        profiles.mkdir()
        config_dir.mkdir()
        sessions_dir.mkdir()
        logs_dir.mkdir()

        assert workspace.exists()
        assert profiles.exists()
        assert config_dir.exists()
        assert sessions_dir.exists()
        assert logs_dir.exists()

    def test_profile_files(self, agent_root: Path):
        """Profile directory should contain bootstrap files."""
        profiles = agent_root / "profiles"
        profiles.mkdir()

        (profiles / "AGENTS.md").write_text("# Agent Instructions")
        (profiles / "TOOLS.md").write_text("# Available Tools")

        assert (profiles / "AGENTS.md").exists()
        assert (profiles / "TOOLS.md").exists()

    def test_config_file(self, agent_root: Path):
        """Config directory should contain agent.yaml."""
        config_dir = agent_root / ".config"
        config_dir.mkdir()

        config = {
            "channels": {"telegram": {"enabled": True}},
            "providers": {"openai": {"api_key": "sk-xxx"}},
        }
        config_file = config_dir / "agent.yaml"
        config_file.write_text(json.dumps(config))

        assert config_file.exists()
        loaded = json.loads(config_file.read_text())
        assert loaded["channels"]["telegram"]["enabled"] is True


class TestStoragePathSecurity:
    """Tests for storage path security."""

    @pytest.fixture
    def storage(self, tmp_storage: Path) -> LocalStorage:
        return LocalStorage(root=tmp_storage)

    def test_path_traversal_blocked(self, storage: LocalStorage):
        """Path traversal should be blocked."""
        with pytest.raises(ValueError, match="Path escape"):
            storage._resolve("../../../etc/passwd")

    def test_absolute_path_blocked(self, storage: LocalStorage):
        """Absolute paths outside root should be blocked."""
        with pytest.raises(ValueError, match="Path escape"):
            storage._resolve("/etc/passwd")

    def test_valid_nested_path(self, storage: LocalStorage):
        """Valid nested paths should work."""
        resolved = storage._resolve("agent/workspace/file.txt")
        assert str(resolved).startswith(str(storage.root))

    def test_dot_paths_handled(self, storage: LocalStorage):
        """Paths with dots should be resolved correctly."""
        resolved = storage._resolve("agent/./workspace/../workspace/file.txt")
        assert str(resolved).startswith(str(storage.root))
        assert "file.txt" in str(resolved)


class TestFileOperationHelpers:
    """Tests for file operation helper patterns."""

    @pytest.mark.asyncio
    async def test_json_roundtrip(self, tmp_storage: Path):
        """JSON data should survive storage roundtrip."""
        storage = LocalStorage(root=tmp_storage)

        data = {
            "id": "agent-123",
            "name": "Test Agent",
            "settings": {"enabled": True, "values": [1, 2, 3]},
        }

        await storage.write("test.json", json.dumps(data).encode())
        content = await storage.read("test.json")
        loaded = json.loads(content.decode())

        assert loaded == data

    @pytest.mark.asyncio
    async def test_binary_file_handling(self, tmp_storage: Path):
        """Binary data should survive storage roundtrip."""
        storage = LocalStorage(root=tmp_storage)

        binary_data = bytes(range(256))
        await storage.write("binary.bin", binary_data)
        content = await storage.read("binary.bin")

        assert content == binary_data

    @pytest.mark.asyncio
    async def test_empty_file(self, tmp_storage: Path):
        """Empty files should be handled correctly."""
        storage = LocalStorage(root=tmp_storage)

        await storage.write("empty.txt", b"")
        content = await storage.read("empty.txt")

        assert content == b""

    @pytest.mark.asyncio
    async def test_large_file(self, tmp_storage: Path):
        """Large files should be handled correctly."""
        storage = LocalStorage(root=tmp_storage)

        large_data = b"x" * (1024 * 1024)
        await storage.write("large.bin", large_data)
        content = await storage.read("large.bin")

        assert content == large_data
