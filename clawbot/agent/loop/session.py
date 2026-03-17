"""SessionProcessor: message processing and agent iteration loop."""

import asyncio
import json
from typing import Awaitable, Callable

from loguru import logger

from clawbot.agent.consolidator import MemoryConsolidator
from clawbot.agent.context import ContextBuilder
from clawbot.agent.loop.mcp import McpManager
from clawbot.agent.loop.tools import ToolsManager
from clawbot.agent.tools.utils import strip_think, tool_hint
from clawbot.core.session import Session, SessionManager
from clawbot.providers.base import LLMProvider
from clawlib.bus import InboundMessage, MessageBus, OutboundMessage


def _on_consolidate_done(task: asyncio.Task) -> None:
    """Log consolidation task failures (used as done callback)."""
    if exc := task.exception():
        logger.error("Memory consolidation failed: {}", exc)


class SessionProcessor:
    """Processes messages, manages sessions, and runs the LLM iteration loop."""

    def __init__(
        self,
        tools_manager: ToolsManager,
        mcp_manager: McpManager,
        provider: LLMProvider,
        context: ContextBuilder,
        sessions: SessionManager,
        consolidator: MemoryConsolidator,
        bus: MessageBus,
        model: str,
        temperature: float,
        max_tokens: int,
        max_iterations: int,
        memory_window: int,
        on_event: Callable[..., Awaitable[None]] | None = None,
        software_management=None,
    ) -> None:
        self._tools_manager = tools_manager
        self._mcp_manager = mcp_manager
        self._provider = provider
        self._context = context
        self._sessions = sessions
        self._consolidator = consolidator
        self._bus = bus
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._max_iterations = max_iterations
        self._memory_window = memory_window
        self._on_event = on_event
        self._software_management = software_management

    async def run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[[str], Awaitable[None]] | None = None,
        channel: str = "cli",
        chat_id: str = "direct",
        plan_id: str = "",
    ) -> tuple[str | None, list[str], list[dict]]:
        """
        Run the agent iteration loop.

        Args:
            initial_messages: Starting messages for the LLM conversation.
            on_progress: Optional callback to push intermediate content to the user.
            channel: Channel name (for tool approval prompts).
            chat_id: Chat ID (for tool approval prompts).
            plan_id: Plan ID when in plan context (for tool approval routing).

        Returns:
            Tuple of (final_content, list_of_tools_used, turn_messages).
            turn_messages contains the full assistant+tool message chain for this turn,
            ready to be stored in the session for future context.
        """
        messages = initial_messages
        # Track where the turn-specific messages start so we can save them to session.
        turn_start_idx = len(messages)
        iteration = 0
        final_content = None
        tools_used: list[str] = []

        while iteration < self._max_iterations:
            iteration += 1

            all_tool_defs = (
                self._tools_manager.tools.get_definitions()
                + self._tools_manager.mcp.get_definitions()
            )
            response = await self._provider.chat(
                messages=messages,
                tools=all_tool_defs,
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )

            if response.has_tool_calls:
                if on_progress:
                    await on_progress(tool_hint(response.tool_calls))

                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in response.tool_calls
                ]
                messages = self._context.add_assistant_message(
                    messages,
                    response.content,
                    tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )

                tool_calls = response.tool_calls
                for tc in tool_calls:
                    tools_used.append(tc.name)

                if len(tool_calls) == 1:
                    tc_id, result = await self._tools_manager.execute_tool(
                        tool_calls[0], channel=channel, chat_id=chat_id, plan_id=plan_id
                    )
                    messages = self._context.add_tool_result(
                        messages, tc_id, tool_calls[0].name, result
                    )
                else:
                    results = await asyncio.gather(
                        *(
                            self._tools_manager.execute_tool(
                                tc, channel=channel, chat_id=chat_id, plan_id=plan_id
                            )
                            for tc in tool_calls
                        )
                    )
                    for tc, (tc_id, result) in zip(tool_calls, results):
                        messages = self._context.add_tool_result(messages, tc_id, tc.name, result)
            else:
                final_content = strip_think(response.content)
                break

        # Collect all messages added during this turn (excludes system prompt + prior history).
        turn_messages = messages[turn_start_idx:]
        return final_content, tools_used, turn_messages

    async def process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> OutboundMessage | None:
        """
        Process a single inbound message.

        Args:
            msg: The inbound message to process.
            session_key: Override session key (used by process_direct).
            on_progress: Optional callback for intermediate output (defaults to bus publish).

        Returns:
            The response message, or None if no response needed.
        """
        if msg.channel == "system":
            return await self._process_system_message(msg)

        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info(f"Processing message from {msg.channel}:{msg.sender_id}: {preview}")
        _plan_id = ""
        if msg.channel == "admin" and msg.chat_id.startswith("plan:"):
            _plan_id = msg.chat_id.split(":", 1)[1]
        if self._on_event:
            await self._on_event("message_received", msg.channel, preview, plan_id=_plan_id)
        key = session_key or msg.session_key
        session = self._sessions.get_or_create(key)

        cmd = msg.content.strip().lower()
        if cmd == "/new":
            messages_to_archive = session.messages.copy()
            session.clear()
            self._sessions.save(session)
            self._sessions.invalidate(session.key)

            async def _consolidate_and_cleanup() -> None:
                temp_session = Session(key=session.key)
                temp_session.messages = messages_to_archive
                await self._consolidator.consolidate(
                    temp_session, self._memory_window, archive_all=True
                )

            asyncio.create_task(_consolidate_and_cleanup()).add_done_callback(_on_consolidate_done)
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="New session started. Memory consolidation in progress.",
            )
        if cmd == "/help":
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="🐈 clawbot commands:\n/new — Start a new conversation\n/help — Show available commands",
            )

        if len(session.messages) > self._memory_window:
            task = asyncio.create_task(
                self._consolidator.consolidate(session, self._memory_window, archive_all=False)
            )
            task.add_done_callback(_on_consolidate_done)

        self._tools_manager.set_tool_context(msg.channel, msg.chat_id)
        initial_messages = self._context.build_messages(
            history=session.get_history(max_messages=self._memory_window),
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel,
            chat_id=msg.chat_id,
            tool_approval_config=self._tools_manager.approval_config,
            mcp_tools_summary=self._tools_manager.mcp.get_tools_summary(),
            software_exec_hint=self._software_management.get_spawn_hint()
            if self._software_management
            else None,
            model=self._model,
        )

        async def _bus_progress(content: str) -> None:
            if msg.channel == "acp":
                return
            await self._bus.publish_outbound(
                OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=content,
                    metadata={**(msg.metadata or {}), "type": "progress"},
                )
            )

        final_content, tools_used, turn_messages = await self.run_agent_loop(
            initial_messages,
            on_progress=on_progress or _bus_progress,
            channel=msg.channel,
            chat_id=msg.chat_id,
            plan_id=_plan_id,
        )

        if final_content is None:
            final_content = "I've completed processing but have no response to give."

        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info(f"Response to {msg.channel}:{msg.sender_id}: {preview}")

        session.add_message("user", msg.content)
        if turn_messages:
            # Store the full tool call chain so the LLM knows what it did last turn.
            session.add_raw_messages(turn_messages)
        else:
            session.add_message(
                "assistant", final_content, tools_used=tools_used if tools_used else None
            )
        self._sessions.save(session)
        if self._on_event:
            await self._on_event(
                "message_sent", msg.channel, (final_content or "")[:200], plan_id=_plan_id
            )
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            metadata=msg.metadata or {},
        )

    async def _process_system_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        Process a system message (e.g., subagent announce).

        The chat_id field contains "original_channel:original_chat_id" to route
        the response back to the correct destination.
        """
        logger.info(f"Processing system message from {msg.sender_id}")

        if ":" in msg.chat_id:
            parts = msg.chat_id.split(":", 1)
            origin_channel = parts[0]
            origin_chat_id = parts[1]
        else:
            origin_channel = "cli"
            origin_chat_id = msg.chat_id

        session_key = f"{origin_channel}:{origin_chat_id}"
        session = self._sessions.get_or_create(session_key)
        self._tools_manager.set_tool_context(origin_channel, origin_chat_id)

        _plan_id = ""
        if origin_chat_id.startswith("plan:"):
            _plan_id = origin_chat_id.split(":", 1)[1]

        initial_messages = self._context.build_messages(
            history=session.get_history(max_messages=self._memory_window),
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=origin_channel,
            chat_id=origin_chat_id,
            tool_approval_config=self._tools_manager.approval_config,
            mcp_tools_summary=self._tools_manager.mcp.get_tools_summary(),
            software_exec_hint=self._software_management.get_spawn_hint()
            if self._software_management
            else None,
            model=self._model,
        )
        final_content, _, turn_messages = await self.run_agent_loop(
            initial_messages,
            channel=origin_channel,
            chat_id=origin_chat_id,
            plan_id=_plan_id,
        )

        if final_content is None:
            final_content = "Background task completed."

        session.add_message("user", f"[System: {msg.sender_id}] {msg.content}")
        if turn_messages:
            session.add_raw_messages(turn_messages)
        else:
            session.add_message("assistant", final_content)
        self._sessions.save(session)

        return OutboundMessage(
            channel=origin_channel, chat_id=origin_chat_id, content=final_content
        )

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """
        Process a message directly (for CLI or cron usage).

        Args:
            content: The message content.
            session_key: Session identifier (overrides channel:chat_id for session lookup).
            channel: Source channel (for tool context routing).
            chat_id: Source chat ID (for tool context routing).
            on_progress: Optional callback for intermediate output.

        Returns:
            The agent's response.
        """
        self._mcp_manager.connect()
        msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=content)

        response = await self.process_message(msg, session_key=session_key, on_progress=on_progress)
        if response:
            await self._bus.publish_outbound(response)
        return response.content if response else ""
