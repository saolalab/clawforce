"""Create runtime backend from env config.

Backends:
- process (default): one agent per subprocess (minimal isolation).
- docker: one agent per container (full isolation).
"""

import os
from typing import Any

from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.storage import StorageBackend, get_storage_backend

RUNTIME_BACKENDS = ("process", "docker")


def get_runtime_backend(
    kind: str | None = None,
    storage: StorageBackend | None = None,
    ws_manager: Any = None,
    activity_registry: Any = None,
) -> AgentRuntimeBackend:
    """Return runtime backend by *kind* (or ``ADMIN_RUNTIME_BACKEND`` env, default ``process``)."""
    kind = (
        kind
        or os.environ.get("ADMIN_RUNTIME_BACKEND")
        or os.environ.get("ADMIN_POOL_BACKEND")
        or "process"
    ).lower()
    storage = storage or get_storage_backend()
    if kind == "process":
        from clawforce.core.runtimes.local import LocalRuntime

        return LocalRuntime(
            storage=storage,
            ws_manager=ws_manager,
            activity_registry=activity_registry,
        )
    if kind == "docker":
        from clawforce.core.runtimes.docker import DockerRuntime

        return DockerRuntime(
            storage=storage,
            ws_manager=ws_manager,
            activity_registry=activity_registry,
        )
    raise ValueError(f"Unknown runtime backend: {kind}. Choose from: {RUNTIME_BACKENDS}")
