"""Runtime implementations and factory.

Import runtime classes lazily to avoid requiring optional dependencies (e.g. docker).
Use get_runtime_backend() factory or import specific classes directly.
"""

from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.runtimes.factory import RUNTIME_BACKENDS, get_runtime_backend

__all__ = [
    "AgentRuntimeBackend",
    "RUNTIME_BACKENDS",
    "get_runtime_backend",
]
