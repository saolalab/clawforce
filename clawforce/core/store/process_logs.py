"""Process log store: RAM ring buffer + file persistence for real-time streaming.

Used for Docker runtime: control plane appends lines when streaming from container.
Local runtime writes directly to worker.log; no store involvement.
"""

from collections import deque
from pathlib import Path

from clawforce.core.services.workspace_service import AGENTS_DIR
from clawforce.core.store.agents import AgentStore
from clawlib.storage import get_storage_root


class ProcessLogStore:
    """Per-agent in-memory ring buffer + file append for process logs."""

    def __init__(
        self,
        storage,
        agent_store: AgentStore,
        max_lines: int = 2000,
    ) -> None:
        self._buffers: dict[str, deque[str]] = {}
        self._storage = storage
        self._agent_store = agent_store
        self._max = max_lines

    def _log_path(self, agent_id: str) -> Path | None:
        agent = self._agent_store.get_agent(agent_id)
        if not agent:
            return None
        root = get_storage_root(self._storage)
        if not isinstance(root, Path):
            root = Path(str(root))
        base = agent.base_path or agent_id
        return root / AGENTS_DIR / base / ".logs" / "process.log"

    def append(self, agent_id: str, line: str) -> None:
        """Add line to buffer and append to file."""
        if agent_id not in self._buffers:
            self._buffers[agent_id] = deque(maxlen=self._max)
        self._buffers[agent_id].append(line)
        path = self._log_path(agent_id)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def get_recent(self, agent_id: str, limit: int = 200) -> list[str]:
        """Return last N lines from buffer."""
        buf = self._buffers.get(agent_id)
        if not buf:
            return []
        return list(buf)[-limit:]
