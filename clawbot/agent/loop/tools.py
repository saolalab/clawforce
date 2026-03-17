"""ToolsManager: tool registration, execution, and approval."""

import json
import time
from pathlib import Path

from loguru import logger

from clawbot.agent.agent_fs import AgentFS
from clawbot.agent.approval import ToolApprovalManager
from clawbot.agent.subagent import SubagentManager
from clawbot.agent.tools.a2a import get_a2a_tools
from clawbot.agent.tools.cron import CronTool
from clawbot.agent.tools.filesystem import (
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WorkspaceTreeTool,
    WriteFileTool,
)
from clawbot.agent.tools.message import MessageTool
from clawbot.agent.tools.plan import get_plan_tools
from clawbot.agent.tools.policy import ShellCommandPolicy
from clawbot.agent.tools.registry import ToolRegistry
from clawbot.agent.tools.shell import ExecTool
from clawbot.agent.tools.spawn import SpawnTool
from clawbot.agent.tools.utils import redact_tool_args, truncate_output
from clawbot.agent.tools.web import WebFetchTool, WebSearchTool
from clawbot.providers.base import ToolCallRequest
from clawlib.bus import InboundMessage, MessageBus
from clawlib.config.schema import ExecToolConfig, WebSearchConfig


class ToolsManager:
    """Manages tool registration, context setting, approval, and execution."""

    def __init__(
        self,
        tools: ToolRegistry,
        mcp: ToolRegistry,
        approval: ToolApprovalManager,
        bus: MessageBus,
        subagents: SubagentManager,
        file_service: AgentFS,
        workspace: Path | str,
        exec_config: ExecToolConfig,
        web_search_config: WebSearchConfig,
        restrict_to_workspace: bool,
        ssrf_protection: bool,
        max_tool_output_chars: int,
        admin_api_url: str = "",
        agent_token: str = "",
        agent_id: str = "",
        cron_service=None,
        on_event=None,
    ) -> None:
        self.tools = tools
        self.mcp = mcp
        self._approval = approval
        self._bus = bus
        self._subagents = subagents
        self._file_service = file_service
        self._workspace = Path(workspace) if isinstance(workspace, str) else workspace
        self._exec_config = exec_config
        self._web_search_config = web_search_config
        self._restrict_to_workspace = restrict_to_workspace
        self._ssrf_protection = ssrf_protection
        self._max_tool_output_chars = max_tool_output_chars
        self._admin_api_url = admin_api_url
        self._agent_token = agent_token
        self._agent_id = agent_id
        self._cron_service = cron_service
        self._on_event = on_event

    def register_default_tools(self) -> None:
        """Register the default set of tools."""
        self.tools.register(ReadFileTool(file_service=self._file_service))
        self.tools.register(WriteFileTool(file_service=self._file_service))
        self.tools.register(EditFileTool(file_service=self._file_service))
        self.tools.register(ListDirTool(file_service=self._file_service))
        self.tools.register(WorkspaceTreeTool(file_service=self._file_service))

        shell_policy = ShellCommandPolicy.from_dict(self._exec_config.policy.model_dump())
        self.tools.register(
            ExecTool(
                working_dir=str(self._workspace),
                timeout=self._exec_config.timeout,
                restrict_to_workspace=self._restrict_to_workspace,
                policy=shell_policy,
            )
        )

        self.tools.register(WebSearchTool(config=self._web_search_config))
        self.tools.register(WebFetchTool(ssrf_protection=self._ssrf_protection))

        message_tool = MessageTool(send_callback=self._bus.publish_outbound)
        self.tools.register(message_tool)

        spawn_tool = SpawnTool(manager=self._subagents)
        self.tools.register(spawn_tool)

        if self._cron_service:
            self.tools.register(CronTool(self._cron_service))

        if self._admin_api_url and self._agent_token:
            for tool in get_plan_tools(self._admin_api_url, self._agent_token, self._agent_id):
                self.tools.register(tool)
            logger.info("Registered plan tools (admin_url={})", self._admin_api_url)

            for tool in get_a2a_tools(self._admin_api_url, self._agent_token, self._agent_id):
                self.tools.register(tool)
            logger.info("Registered A2A tools")

        self.tools.register_plugins()

    def set_tool_context(self, channel: str, chat_id: str) -> None:
        """Update context for tools that need routing info (message, spawn, cron).

        Call before each agent run; tools use this to route replies to the correct channel/chat.
        """
        if message_tool := self.tools.get("message"):
            message_tool.set_context(channel, chat_id)
        if spawn_tool := self.tools.get("spawn"):
            spawn_tool.set_context(channel, chat_id)
        if cron_tool := self.tools.get("cron"):
            cron_tool.set_context(channel, chat_id)

    @property
    def approval_config(self):
        """Tool approval config (for context builder)."""
        return self._approval.config

    def try_resolve_approval(self, msg: InboundMessage) -> bool:
        """If this message is a yes/no reply for a pending tool approval, resolve the future and return True."""
        return self._approval.try_resolve(msg)

    async def execute_tool(
        self,
        tool_call: ToolCallRequest,
        channel: str,
        chat_id: str,
        plan_id: str = "",
    ) -> tuple[str, str]:
        """Execute a single tool call with logging and truncation.

        If tool approval is ask_before_run, prompts the user in-channel and waits for approval.
        Returns (tool_call_id, result_text).
        """
        mode = self._approval.get_mode(tool_call.name)
        if mode == "ask_before_run":
            logger.info(
                "[tool_approval] Requesting approval for tool={}, channel={}, chat_id={}",
                tool_call.name,
                channel,
                chat_id,
            )
            approved = await self._approval.request_approval(tool_call, channel, chat_id)
            logger.info(
                "[tool_approval] Approval result for tool={}: approved={}",
                tool_call.name,
                approved,
            )
            if not approved:
                return (
                    tool_call.id,
                    f"[APPROVAL REQUIRED] The user did not approve running '{tool_call.name}' "
                    f"(either replied 'no' or didn't respond within the timeout). "
                    "This is not a system error - you can still use this tool if the user agrees. "
                    "Ask the user if they want you to try again.",
                )

        args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
        logger.info("Tool call: {}({})", tool_call.name, args_str[:200])
        start = time.perf_counter()
        result_status = "ok"
        if self._on_event:
            hint = args_str[:80]
            await self._on_event(
                "tool_call",
                "",
                hint,
                tool_name=tool_call.name,
                tool_args_redacted=redact_tool_args(tool_call.arguments),
                plan_id=plan_id,
            )

        try:
            if tool_call.name in self.mcp:
                result = await self.mcp.execute(tool_call.name, tool_call.arguments)
            else:
                result = await self.tools.execute(tool_call.name, tool_call.arguments)
        except Exception as e:
            result_status = "error"
            result = f"Error executing {tool_call.name}: {e}"
        result = truncate_output(result, self._max_tool_output_chars)
        duration_ms = round((time.perf_counter() - start) * 1000)

        if self._on_event:
            await self._on_event(
                "tool_result",
                "",
                str(result)[:120],
                tool_name=tool_call.name,
                tool_args_redacted=redact_tool_args(tool_call.arguments),
                result_status=result_status,
                duration_ms=duration_ms,
                plan_id=plan_id,
            )
        return tool_call.id, result
