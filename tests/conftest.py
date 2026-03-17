"""Pytest fixtures shared across all test modules."""

import asyncio
from pathlib import Path

import pytest


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    """Temporary storage directory for tests."""
    storage = tmp_path / "storage"
    storage.mkdir(parents=True, exist_ok=True)
    return storage


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Temporary workspace directory for tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
