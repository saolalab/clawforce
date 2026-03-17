"""Agent-to-Agent (A2A) communication tools.

Allows agents to discover and call each other directly.
Tools call the admin API for inter-agent messaging.
"""

from typing import Any

import httpx

from clawbot.agent.tools.base import Tool


def _api_base(url: str) -> str:
    """Ensure admin URL has no trailing slash and includes /api if missing."""
    u = url.rstrip("/")
    if not u.endswith("/api"):
        u = f"{u}/api"
    return u


class _A2AToolBase(Tool):
    """Shared base for A2A tools that call the admin API."""

    def __init__(self, admin_base_url: str, agent_token: str, agent_id: str) -> None:
        self._base = _api_base(admin_base_url)
        self._token = agent_token
        self._agent_id = agent_id

    async def _api_call(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        label: str,
        timeout: float = 60.0,
    ) -> dict | list | str:
        """Authenticated API call. Returns parsed JSON on success, error string on failure."""
        url = f"{self._base}{path}"
        headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                req_kwargs: dict[str, Any] = {}
                if payload is not None:
                    req_kwargs["json"] = payload
                r = await client.request(method, url, headers=headers, **req_kwargs)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            return f"Error {label}: {e.response.status_code} {e.response.text}"
        except httpx.RequestError as e:
            return f"Error calling admin API: {e!s}"


class A2ACallTool(_A2AToolBase):
    """Send a direct message to another agent in the same team."""

    @property
    def name(self) -> str:
        return "a2a_call"

    @property
    def description(self) -> str:
        return (
            "Send a direct message to another agent (A2A). "
            "The target agent must be running. "
            "Use a2a_discover() first to confirm the agent is available and get their id. "
            "For task-based communication visible to all agents and the admin, prefer "
            "add_task_comment() with @agent_name — this creates a persistent record. "
            "Use a2a_call for urgent real-time coordination that needs immediate attention."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_agent_id": {
                    "type": "string",
                    "description": "The ID of the agent to message.",
                },
                "message": {
                    "type": "string",
                    "description": "The message to send to the target agent.",
                },
            },
            "required": ["target_agent_id", "message"],
        }

    async def execute(self, target_agent_id: str = "", message: str = "", **kwargs: Any) -> str:
        if not target_agent_id:
            return "Error: target_agent_id is required"
        if not message:
            return "Error: message is required"
        if target_agent_id == self._agent_id:
            return "Cannot send a message to yourself."

        result = await self._api_call(
            "POST",
            f"/agents/{target_agent_id}/a2a-message",
            {"message": message},
            label="sending A2A message",
            timeout=130.0,
        )
        if isinstance(result, str):
            return result
        return result.get("reply", "Agent responded with no content.")


class A2ADiscoverTool(_A2AToolBase):
    """Discover other agents available in the same team."""

    @property
    def name(self) -> str:
        return "a2a_discover"

    @property
    def description(self) -> str:
        return (
            "List all other agents you can communicate with via A2A. "
            "Use this when the user asks about your peers, teammates, or who other agents are. "
            "Shows agent ID, name, description, and whether they are currently running. "
            "If you need to assign tasks to a plan, use list_plan_assignees(plan_id) instead."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> str:
        result = await self._api_call(
            "GET",
            "/agents/me/peers",
            label="discovering peers",
        )
        if isinstance(result, str):
            return result
        if not isinstance(result, list):
            return str(result)
        if not result:
            return (
                "No other agents found via A2A discovery.\n\n"
                "This can happen if no other agents exist yet.\n\n"
                "If you are coordinating a plan, use `list_plan_assignees(plan_id)` to see ALL available agents "
                "and use `assign_plan_task` to delegate work. After the plan is activated, assigned agents can "
                "communicate via task comments (`add_task_comment` with @mentions) or A2A."
            )

        lines = ["## Available agents (A2A peers)\n"]
        for a in result:
            status = a.get("status", "unknown")
            status_icon = "running" if status == "running" else "not running"
            desc = a.get("description", "")
            desc_str = f" — {desc}" if desc else ""
            lines.append(f"- **{a.get('name', '?')}** (id=`{a['id']}`, {status_icon}){desc_str}")

        lines.append("")
        lines.append(
            "Use `a2a_call(target_agent_id, message)` to send a direct message to a running agent. "
            "For task-based coordination, use `add_task_comment` with @mentions."
        )
        return "\n".join(lines)


def get_a2a_tools(admin_base_url: str, agent_token: str, agent_id: str) -> list[Tool]:
    """Return A2A tools configured for the given admin API."""
    return [
        A2ADiscoverTool(admin_base_url, agent_token, agent_id),
        A2ACallTool(admin_base_url, agent_token, agent_id),
    ]
