"""Agent runtime backend abstract base class."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator

from clawlib.activity import ActivityEvent

logger = logging.getLogger(__name__)


class AgentRuntimeError(Exception):
    """Raised when a runtime operation fails (agent disabled, not found, already running, etc.)."""


@dataclass
class AgentStatus:
    """Status of a single agent instance (workload state).

    status: stopped | running | failed
    """

    agent_id: str
    status: str  # stopped | running | failed
    message: str = ""
    mcp: dict | None = None
    software_warnings: list[dict] | None = None
    software_installing: bool = False


class AgentRuntimeBackend(ABC):
    """Runtime backend for agent workloads (process, docker, k8s, etc.).

    Like a container runtime or scheduler: the control plane uses the runtime to
    start/stop agent instances and to read/write agent data (config, workspace,
    profiles). For process/docker backends the runtime talks to the worker over WebSocket.
    """

    @abstractmethod
    async def start_agent(self, agent_id: str) -> None: ...

    @abstractmethod
    async def stop_agent(self, agent_id: str) -> None: ...

    @abstractmethod
    async def get_status(self, agent_id: str) -> AgentStatus: ...

    @abstractmethod
    async def send_message(
        self,
        agent_id: str,
        message: str,
        context: dict | None = None,
    ) -> str: ...

    def subscribe_activity(self, agent_id: str) -> AsyncIterator[ActivityEvent]:
        async def _empty() -> AsyncIterator[ActivityEvent]:
            return
            yield  # type: ignore[misc]

        return _empty()

    def get_recent_activity(self, agent_id: str, limit: int = 50) -> list[ActivityEvent]:
        return []

    def emit_activity(self, agent_id: str, event: ActivityEvent) -> None:
        """Inject a synthetic activity event into the agent's activity log.

        Used by server-side code (e.g. plan task status changes) to write events
        that aren't emitted by the agent loop itself.
        """

    def supports_terminal(self) -> bool:
        """Return True if this runtime supports the terminal WebSocket (e.g. Docker exec, local PTY)."""
        return False

    def get_terminal_target(self, agent_id: str) -> tuple[str, Any] | None:
        """Return (kind, target) for terminal bridge, or None if agent not running or terminal unsupported.

        kind is \"docker\" (target is container) or \"local\" (target is agent_root path str).
        """
        return None

    async def list_workspace(self, agent_id: str) -> list[str]:
        """Return list of file paths in the agent workspace."""
        return []

    async def read_workspace_file(self, agent_id: str, path: str) -> str | None:
        """Return file content as string, or None if not found."""
        return None

    async def write_workspace_file(self, agent_id: str, path: str, content: str) -> bool:
        """Write content to a workspace file. Returns True on success."""
        return False

    async def delete_workspace_file(self, agent_id: str, path: str) -> bool:
        """Delete a file or directory in the workspace. Returns True on success."""
        return False

    async def rename_workspace_file(self, agent_id: str, path: str, new_name: str) -> bool:
        """Rename a file or directory in the workspace. Returns True on success."""
        return False

    async def move_workspace_file(self, agent_id: str, src_path: str, dest_path: str) -> bool:
        """Move a file or directory in the workspace. Returns True on success."""
        return False

    async def list_profile(self, agent_id: str) -> list[str]:
        """Return list of file paths in the agent profile (character setup)."""
        return []

    async def read_profile_file(self, agent_id: str, path: str) -> str | None:
        """Return profile file content as string, or None if unavailable."""
        return None

    async def write_profile_file(self, agent_id: str, path: str, content: str) -> bool:
        """Write content to a profile file. Returns True on success."""
        return False

    async def get_config(self, agent_id: str) -> dict | None:
        """Return the agent's parsed config as a dict, or None if unavailable."""
        return None

    async def update_config(self, agent_id: str, body: dict) -> dict | None:
        """Merge *body* into the agent's config and return the updated config dict."""
        return None

    async def update_secrets(self, agent_id: str, body: dict) -> bool:
        """Push secrets (e.g. providers) to the running agent for hot-reload. Returns True on success."""
        return False

    async def apply_config(self, agent_id: str, config: dict) -> dict | None:
        """Persist and push config to running agent. Caller must have already persisted.

        If agent is online: pushes plain config via put_config, secrets via put_secrets.
        Returns updated config dict or None if offline.
        """
        return None

    async def install_skill(
        self,
        agent_id: str,
        slug: str,
        env: dict[str, str] | None = None,
    ) -> dict:
        """Install a skill from the registry into the agent's workspace. Returns result dict."""
        raise AgentRuntimeError("install_skill not implemented")

    async def uninstall_skill(self, agent_id: str, slug: str) -> dict:
        """Remove an installed skill from the agent's workspace. Returns result dict."""
        raise AgentRuntimeError("uninstall_skill not implemented")

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
    ) -> dict:
        """Install a software (npm/pip) into the agent and add to config. Returns result dict."""
        raise AgentRuntimeError("install_software not implemented")

    async def uninstall_software(self, agent_id: str, slug: str) -> dict:
        """Uninstall a software from the agent and remove from config. Returns result dict."""
        raise AgentRuntimeError("uninstall_software not implemented")

    async def activate_plan(
        self,
        plan_id: str,
        agent_ids: list[str],
        plan_context_message: str,
    ) -> dict:
        """Send plan context to already-running agents. Returns status per agent."""
        results = {}
        for aid in agent_ids:
            status = await self.get_status(aid)
            if status.status != "running":
                results[aid] = {"ok": False, "error": "not_running"}
                continue
            try:
                await self.send_message(
                    aid,
                    plan_context_message,
                    context={
                        "session_key": f"plan:{plan_id}",
                        "plan_id": plan_id,
                        "channel": "admin",
                        "chat_id": f"plan:{plan_id}",
                    },
                )
                results[aid] = {"ok": True}
            except Exception as exc:
                results[aid] = {"ok": False, "error": str(exc)}
        return results

    async def deactivate_plan(self, plan_id: str, agent_ids: list[str]) -> None:
        """Notify agents that a plan is paused. Does NOT stop agents."""
        for aid in agent_ids:
            try:
                await self.send_message(
                    aid,
                    f"Plan `{plan_id}` has been paused. You may continue working on other tasks.",
                    context={
                        "session_key": f"plan:{plan_id}",
                        "plan_id": plan_id,
                        "channel": "admin",
                        "chat_id": f"plan:{plan_id}",
                    },
                )
            except Exception as exc:
                logger.warning(f"Failed to notify agent {aid} of plan deactivation: {exc}")

    async def complete_plan(self, plan_id: str, plan_name: str, agent_ids: list[str]) -> None:
        """Notify agents that a plan is completed. Does NOT stop agents."""
        for aid in agent_ids:
            try:
                await self.send_message(
                    aid,
                    (
                        f"Plan **{plan_name}** (`{plan_id}`) has been marked as **completed** by admin. "
                        "No further work is required on this plan. "
                        "Do not create, update, or move any tasks on it."
                    ),
                    context={
                        "session_key": f"plan:{plan_id}",
                        "plan_id": plan_id,
                        "channel": "admin",
                        "chat_id": f"plan:{plan_id}",
                    },
                )
            except Exception as exc:
                logger.warning(f"Failed to notify agent {aid} of plan completion: {exc}")
