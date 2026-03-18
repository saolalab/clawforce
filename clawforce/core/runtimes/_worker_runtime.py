"""Base class for runtime backends that run agent instances as workers (process or container).

Control plane communicates with the worker over WebSocket only:
admin sends ``{"type": "request", ...}``, worker replies ``{"type": "response", ...}``.
Workspace/config/profile operations require the agent instance to be running.
"""

from abc import abstractmethod
from typing import Any, AsyncIterator

from clawforce.core.database import get_database
from clawforce.core.domain.runtime import AgentRuntimeBackend, AgentRuntimeError, AgentStatus
from clawforce.core.storage import StorageBackend, get_storage_backend
from clawforce.core.store.agents import AgentStore
from clawforce.core.ws import ConnectionManager
from clawlib.activity import ActivityEvent
from clawlib.config.helpers import SECRET_SECTIONS


class WorkerRuntimeBase(AgentRuntimeBackend):
    """Shared base for runtime backends that run one worker per agent (WebSocket-only; no storage fallback)."""

    def __init__(
        self,
        storage: StorageBackend | None = None,
        ws_manager: ConnectionManager | None = None,
        activity_registry: Any = None,
    ) -> None:
        self._storage = storage or get_storage_backend()
        self._store = AgentStore(get_database(), self._storage)
        self._running: dict[str, dict[str, Any]] = {}
        self._ws_manager = ws_manager
        self._activity_registry = activity_registry

    def is_running(self, agent_id: str) -> bool:
        """Return True if agent_id has an active worker entry in this runtime."""
        return agent_id in self._running

    def running_agent_ids(self) -> list[str]:
        """Return IDs of all agents with an active worker entry."""
        return list(self._running.keys())

    def _is_ws_connected(self, agent_id: str) -> bool:
        return bool(self._ws_manager and self._ws_manager.is_connected(agent_id))

    async def _ws_request(
        self, agent_id: str, action: str, timeout: float = 15.0, **kwargs: Any
    ) -> dict | None:
        """Send a request over WebSocket and await the response.

        Returns the response dict on success, None if disconnected or timed out.
        """
        if not self._ws_manager:
            return None
        payload: dict = {"type": "request", "action": action, **kwargs}
        return await self._ws_manager.request(agent_id, payload, timeout=timeout)

    @abstractmethod
    async def start_agent(self, agent_id: str) -> None: ...

    @abstractmethod
    async def stop_agent(self, agent_id: str) -> None: ...

    async def get_status(self, agent_id: str) -> AgentStatus:
        """Return agent status. Store is source of truth; 'running' only when WS connected."""
        if self._is_ws_connected(agent_id):
            resp = await self._ws_request(agent_id, "get_health", timeout=5.0)
            if resp and resp.get("ok"):
                data = resp.get("data", {})
                return AgentStatus(
                    agent_id=agent_id,
                    status="running",
                    mcp=data.get("mcp"),
                    software_warnings=data.get("software_warnings"),
                    software_installing=data.get("software_installing", False),
                )
            return AgentStatus(agent_id=agent_id, status="running")
        if agent_id in self._running and not await self._is_worker_alive(agent_id):
            return AgentStatus(agent_id=agent_id, status="stopped", message="Worker exited")
        agent = self._store.get_agent(agent_id)
        return AgentStatus(agent_id=agent_id, status=agent.status if agent else "stopped")

    @abstractmethod
    async def _is_worker_alive(self, agent_id: str) -> bool:
        """Check if the underlying worker process/container is still alive."""
        ...

    def subscribe_activity(self, agent_id: str) -> AsyncIterator[ActivityEvent]:
        if self._activity_registry and self._is_ws_connected(agent_id):
            return self._activity_registry.get_or_create(agent_id).subscribe()

        async def _empty() -> AsyncIterator[ActivityEvent]:
            return
            yield  # type: ignore[misc]

        return _empty()

    def get_recent_activity(self, agent_id: str, limit: int = 50) -> list[ActivityEvent]:
        if self._activity_registry and self._is_ws_connected(agent_id):
            log = self._activity_registry.get_or_create(agent_id)
            return log.recent(limit)
        return []

    def emit_activity(self, agent_id: str, event: ActivityEvent) -> None:
        """Inject a synthetic activity event into the agent's activity log."""
        if self._activity_registry:
            self._activity_registry.get_or_create(agent_id).emit(event)

    # -- Helpers ---------------------------------------------------------------

    def _require_ws(self, agent_id: str) -> None:
        """Raise if the agent is not connected over WebSocket."""
        if not self._is_ws_connected(agent_id):
            raise AgentRuntimeError(f"Agent {agent_id} is not connected")

    # -- Workspace & profile -------------------------------------------------

    async def list_workspace(self, agent_id: str) -> list[str]:
        self._require_ws(agent_id)
        resp = await self._ws_request(agent_id, "list_workspace", root="workspace")
        if resp and resp.get("ok"):
            return resp.get("data", {}).get("files", [])
        return []

    async def read_workspace_file(self, agent_id: str, path: str) -> str | None:
        self._require_ws(agent_id)
        resp = await self._ws_request(agent_id, "read_file", path=path, timeout=10.0)
        if resp and resp.get("ok"):
            return resp.get("data", {}).get("content")
        return None

    async def write_workspace_file(self, agent_id: str, path: str, content: str) -> bool:
        self._require_ws(agent_id)
        resp = await self._ws_request(
            agent_id, "write_file", path=path, content=content, timeout=10.0
        )
        return bool(resp and resp.get("ok"))

    async def delete_workspace_file(self, agent_id: str, path: str) -> bool:
        self._require_ws(agent_id)
        resp = await self._ws_request(agent_id, "delete_file", path=path, timeout=10.0)
        return bool(resp and resp.get("ok"))

    async def rename_workspace_file(self, agent_id: str, path: str, new_name: str) -> bool:
        self._require_ws(agent_id)
        resp = await self._ws_request(
            agent_id, "rename_file", path=path, new_name=new_name, timeout=10.0
        )
        return bool(resp and resp.get("ok"))

    async def move_workspace_file(self, agent_id: str, src_path: str, dest_path: str) -> bool:
        self._require_ws(agent_id)
        resp = await self._ws_request(
            agent_id, "move_file", src_path=src_path, dest_path=dest_path, timeout=10.0
        )
        return bool(resp and resp.get("ok"))

    async def list_profile(self, agent_id: str) -> list[str]:
        self._require_ws(agent_id)
        resp = await self._ws_request(agent_id, "list_workspace", root="profiles")
        if resp and resp.get("ok"):
            return resp.get("data", {}).get("files", [])
        return []

    async def read_profile_file(self, agent_id: str, path: str) -> str | None:
        self._require_ws(agent_id)
        resp = await self._ws_request(agent_id, "read_file", path=f"profiles/{path}", timeout=10.0)
        if resp and resp.get("ok"):
            return resp.get("data", {}).get("content")
        return None

    async def write_profile_file(self, agent_id: str, path: str, content: str) -> bool:
        self._require_ws(agent_id)
        resp = await self._ws_request(
            agent_id, "write_file", path=f"profiles/{path}", content=content, timeout=10.0
        )
        return bool(resp and resp.get("ok"))

    # -- Config --------------------------------------------------------------

    async def get_config(self, agent_id: str) -> dict | None:
        self._require_ws(agent_id)
        resp = await self._ws_request(agent_id, "get_config", timeout=10.0)
        if resp and resp.get("ok"):
            return resp.get("data")
        return None

    async def update_config(self, agent_id: str, body: dict) -> dict | None:
        self._require_ws(agent_id)
        resp = await self._ws_request(agent_id, "put_config", body=body, timeout=10.0)
        if resp and resp.get("ok"):
            return resp.get("data")
        return None

    async def update_secrets(self, agent_id: str, body: dict) -> bool:
        """Push secrets to the running agent for hot-reload (e.g. provider API keys)."""
        resp = await self._ws_request(agent_id, "put_secrets", body=body, timeout=10.0)
        return bool(resp and resp.get("ok"))

    async def apply_config(self, agent_id: str, config: dict) -> dict | None:
        """Push plain config and full secrets to running agent. Returns updated config or None if offline."""
        if not self._is_ws_connected(agent_id):
            return None
        plain = {k: v for k, v in config.items() if k not in SECRET_SECTIONS}
        secrets_payload = {
            k: config[k] for k in ("providers", "channels") if k in config and config[k]
        }
        try:
            if plain:
                await self.update_config(agent_id, plain)
            if secrets_payload:
                await self.update_secrets(agent_id, secrets_payload)
            return await self.get_config(agent_id) or config
        except AgentRuntimeError:
            return None

    # -- Skills --------------------------------------------------------------

    async def install_skill(
        self,
        agent_id: str,
        slug: str,
        env: dict[str, str] | None = None,
    ) -> dict:
        if not self._is_ws_connected(agent_id):
            raise AgentRuntimeError(f"Agent {agent_id} is not connected")
        resp = await self._ws_request(
            agent_id, "install_skill", slug=slug, env=env or {}, timeout=90.0
        )
        if resp and resp.get("ok"):
            return resp.get("data", {})
        error = (resp or {}).get("error") if resp else None
        if not error:
            raise AgentRuntimeError(
                "Install failed: request timed out or agent disconnected. "
                "Ensure the agent is running and Node.js is available for npx skills."
            )
        if error.startswith("Install failed"):
            raise AgentRuntimeError(error)
        raise AgentRuntimeError(f"Install failed: {error}")

    async def uninstall_skill(self, agent_id: str, slug: str) -> dict:
        if not self._is_ws_connected(agent_id):
            raise AgentRuntimeError(f"Agent {agent_id} is not connected")
        resp = await self._ws_request(agent_id, "uninstall_skill", slug=slug, timeout=10.0)
        if resp and resp.get("ok"):
            return resp.get("data", {})
        error = (resp or {}).get("error", "Unknown error")
        raise AgentRuntimeError(f"Uninstall failed: {error}")

    async def install_software(
        self,
        agent_id: str,
        slug: str,
        package: str,
        install_type: str,
        name: str = "",
        description: str = "",
        skill_content: str = "",
        command: str = "",
        args: list[str] | None = None,
        stdin: bool = False,
        env: dict[str, str] | None = None,
        post_install: dict | None = None,
    ) -> dict:
        if not self._is_ws_connected(agent_id):
            raise AgentRuntimeError(f"Agent {agent_id} is not connected")
        resp = await self._ws_request(
            agent_id,
            "install_software",
            slug=slug,
            package=package,
            install_type=install_type,
            name=name,
            description=description,
            skill_content=skill_content,
            command=command,
            args=args or [],
            stdin=stdin,
            env=env or {},
            post_install=post_install,
            timeout=90.0,
        )
        if resp and resp.get("ok"):
            return resp.get("data", {})
        error = (resp or {}).get("error", "Unknown error")
        raise AgentRuntimeError(f"Install software failed: {error}")

    async def uninstall_software(self, agent_id: str, slug: str) -> dict:
        if not self._is_ws_connected(agent_id):
            raise AgentRuntimeError(f"Agent {agent_id} is not connected")
        resp = await self._ws_request(agent_id, "uninstall_software", slug=slug, timeout=75.0)
        if resp and resp.get("ok"):
            return resp.get("data", {})
        error = (resp or {}).get("error", "Unknown error")
        raise AgentRuntimeError(f"Uninstall software failed: {error}")

    async def send_message(
        self,
        agent_id: str,
        message: str,
        context: dict | None = None,
    ) -> str:
        ctx = context or {}
        if self._ws_manager and self._ws_manager.is_connected(agent_id):
            ok = await self._ws_manager.send_to_agent(
                agent_id,
                {
                    "type": "message",
                    "text": message,
                    "session_key": ctx.get("session_key", "cli:direct"),
                    "channel": ctx.get("channel", "cli"),
                    "chat_id": ctx.get("chat_id", "direct"),
                },
            )
            if ok:
                return ""
            return "Agent WebSocket disconnected."
        return "Agent is not connected."
