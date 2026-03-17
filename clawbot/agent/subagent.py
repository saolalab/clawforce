"""Subagent manager for background task execution."""

import asyncio
import json
import time as _time
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from clawbot.agent.agent_fs import AgentFS
from clawbot.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from clawbot.agent.tools.registry import ToolRegistry
from clawbot.agent.tools.shell import ExecTool
from clawbot.agent.tools.software_exec import SoftwareExecTool
from clawbot.agent.tools.web import WebFetchTool, WebSearchTool
from clawbot.core.config.schema import ExecToolConfig, WebSearchConfig
from clawbot.core.software import SoftwareManagement
from clawbot.providers.base import LLMProvider
from clawlib.bus import InboundMessage, MessageBus


class SubagentManager:
    """
    Manages background subagent execution.

    Subagents are lightweight agent instances that run in the background
    to handle specific tasks. They share the same LLM provider but have
    isolated context and a focused system prompt.
    """

    def __init__(
        self,
        provider: LLMProvider,
        file_service: AgentFS,
        bus: MessageBus,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        web_search_config: WebSearchConfig | None = None,
        exec_config: ExecToolConfig | None = None,
        restrict_to_workspace: bool = True,
        software_management: SoftwareManagement | None = None,
        on_event: Any | None = None,
    ):
        self.provider = provider
        self._file_service = file_service
        self.bus = bus
        self.model = model or provider.get_default_model()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.web_search_config = web_search_config or WebSearchConfig()
        self.exec_config = exec_config or ExecToolConfig()
        self.restrict_to_workspace = restrict_to_workspace
        self._software_management = software_management
        self._on_event = on_event
        self._running_tasks: dict[str, asyncio.Task[None]] = {}

    async def spawn(
        self,
        task: str,
        label: str | None = None,
        origin_channel: str = "cli",
        origin_chat_id: str = "direct",
    ) -> str:
        """
        Spawn a subagent to execute a task in the background.

        Args:
            task: The task description for the subagent.
            label: Optional human-readable label for the task.
            origin_channel: The channel to announce results to.
            origin_chat_id: The chat ID to announce results to.

        Returns:
            Status message indicating the subagent was started.
        """
        task_id = str(uuid.uuid4())[:8]
        display_label = label or task[:30] + ("..." if len(task) > 30 else "")

        origin = {
            "channel": origin_channel,
            "chat_id": origin_chat_id,
        }

        # Create background task
        bg_task = asyncio.create_task(self._run_subagent(task_id, task, display_label, origin))
        self._running_tasks[task_id] = bg_task

        # Cleanup when done
        bg_task.add_done_callback(lambda _: self._running_tasks.pop(task_id, None))

        logger.info(f"Spawned subagent [{task_id}]: {display_label}")
        return f"Subagent [{display_label}] started (id: {task_id}). I'll notify you when it completes."

    async def _emit(self, ev_type: str, content: str, **kwargs: Any) -> None:
        """Emit an activity event if an on_event callback is configured."""
        if self._on_event:
            await self._on_event(ev_type, "subagent", content, **kwargs)

    async def _run_subagent(
        self,
        task_id: str,
        task: str,
        label: str,
        origin: dict[str, str],
    ) -> None:
        """Execute the subagent task and announce the result."""
        logger.info(f"Subagent [{task_id}] starting task: {label}")
        await self._emit("subagent_started", label, tool_name=label)

        try:
            # Build subagent tools (no message tool, no spawn tool)
            tools = ToolRegistry()
            tools.register(ReadFileTool(file_service=self._file_service))
            tools.register(WriteFileTool(file_service=self._file_service))
            tools.register(EditFileTool(file_service=self._file_service))
            tools.register(ListDirTool(file_service=self._file_service))
            tools.register(
                ExecTool(
                    working_dir=str(self._file_service.workspace_path),
                    timeout=self.exec_config.timeout,
                    restrict_to_workspace=self.restrict_to_workspace,
                )
            )
            tools.register(WebSearchTool(config=self.web_search_config))
            tools.register(WebFetchTool())
            if self._software_management:
                tools.register(
                    SoftwareExecTool(
                        software_management=self._software_management,
                        workspace=self._file_service.workspace_path,
                    )
                )

            # Build messages with subagent-specific prompt
            system_prompt = self._build_subagent_prompt(task)
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task},
            ]

            # Run agent loop (limited iterations)
            max_iterations = 15
            iteration = 0
            final_result: str | None = None

            while iteration < max_iterations:
                iteration += 1

                response = await self.provider.chat(
                    messages=messages,
                    tools=tools.get_definitions(),
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                if response.has_tool_calls:
                    # Add assistant message with tool calls
                    tool_call_dicts = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in response.tool_calls
                    ]
                    messages.append(
                        {
                            "role": "assistant",
                            "content": response.content or "",
                            "tool_calls": tool_call_dicts,
                        }
                    )

                    # Execute tools
                    for tool_call in response.tool_calls:
                        args_str = json.dumps(tool_call.arguments)
                        logger.debug(
                            f"Subagent [{task_id}] executing: {tool_call.name} with arguments: {args_str}"
                        )
                        await self._emit(
                            "tool_call",
                            args_str[:80],
                            tool_name=tool_call.name,
                            tool_args_redacted=args_str[:80],
                        )
                        _t0 = _time.perf_counter()
                        result = await tools.execute(tool_call.name, tool_call.arguments)
                        duration_ms = round((_time.perf_counter() - _t0) * 1000)
                        await self._emit(
                            "tool_result",
                            str(result)[:120],
                            tool_name=tool_call.name,
                            tool_args_redacted=args_str[:80],
                            result_status="ok",
                            duration_ms=duration_ms,
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_call.name,
                                "content": result,
                            }
                        )
                else:
                    final_result = response.content
                    break

            if final_result is None:
                final_result = "Task completed but no final response was generated."

            logger.info(f"Subagent [{task_id}] completed successfully")
            await self._emit("subagent_done", (final_result or "")[:200], tool_name=label)
            await self._announce_result(task_id, label, task, final_result, origin, "ok")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Subagent [{task_id}] failed: {e}")
            await self._emit(
                "subagent_done", error_msg[:200], tool_name=label, result_status="error"
            )
            await self._announce_result(task_id, label, task, error_msg, origin, "error")

    async def _announce_result(
        self,
        task_id: str,
        label: str,
        task: str,
        result: str,
        origin: dict[str, str],
        status: str,
    ) -> None:
        """Announce the subagent result to the main agent via the message bus."""
        status_text = "completed successfully" if status == "ok" else "failed"

        announce_content = f"""[Subagent '{label}' {status_text}]

Task: {task}

Result:
{result}

Summarize this naturally for the user. Keep it brief (1-2 sentences). Do not mention technical details like "subagent" or task IDs."""

        # Inject as system message to trigger main agent
        msg = InboundMessage(
            channel="system",
            sender_id="subagent",
            chat_id=f"{origin['channel']}:{origin['chat_id']}",
            content=announce_content,
        )

        await self.bus.publish_inbound(msg)
        logger.debug(
            f"Subagent [{task_id}] announced result to {origin['channel']}:{origin['chat_id']}"
        )

    def _build_subagent_prompt(self, task: str) -> str:
        """Build a focused system prompt for the subagent."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = _time.strftime("%Z") or "UTC"

        return f"""# Subagent

## Current Time
{now} ({tz})

You are a subagent spawned by the main agent to complete a specific task.

## Rules
1. Stay focused - complete only the assigned task, nothing else
2. Your final response will be reported back to the main agent
3. Do not initiate conversations or take on side tasks
4. Be concise but informative in your findings

## What You Can Do
- Read and write files in the workspace
- Execute shell commands (restricted to workspace)
- Run installed software via software_exec (backend_key + task; catalog is live, no restart needed)
- Search the web and fetch web pages
- Complete the task thoroughly

## What You Cannot Do
- Send messages directly to users (no message tool available)
- Spawn other subagents
- Access the main agent's conversation history
- Access any file or path outside your workspace

## Workspace
Your workspace is at: {self._file_service.workspace_path}
Skills are available at: {self._file_service.workspace_path}/.agents/skills/ (read SKILL.md files as needed)

All file paths you create or reference MUST be within this workspace.
Do NOT invent or guess paths outside your workspace.

When you have completed the task, provide a clear summary of your findings or actions."""

    def get_running_count(self) -> int:
        """Return the number of currently running subagents."""
        return len(self._running_tasks)
