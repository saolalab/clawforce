"""Tool approval domain: user confirmation before running selected tools."""

import asyncio
import json
from typing import Any

from loguru import logger

from clawlib.bus import InboundMessage, MessageBus, OutboundMessage
from clawlib.config.schema import ToolApprovalConfig


class ToolApprovalManager:
    """
    Manages tool approval state: per-tool mode (always_run / ask_before_run),
    pending futures, and in-channel approval prompts with timeout.
    """

    def __init__(self, bus: MessageBus, config: ToolApprovalConfig):
        self._bus = bus
        self._config = config
        self._pending_approvals: dict[str, asyncio.Future[bool]] = {}
        logger.info(
            f"[tool_approval_init] Initial config: default_mode={self._config.default_mode}, "
            f"per_tool={self._config.per_tool}"
        )

    @property
    def config(self) -> ToolApprovalConfig:
        """Current tool approval config (e.g. for context.build_messages)."""
        return self._config

    def update_config(self, cfg: ToolApprovalConfig) -> None:
        """Hot-reload tool approval config (called when admin updates config)."""
        logger.info(
            f"[update_tool_approval] Updating config: default_mode={cfg.default_mode}, "
            f"per_tool={cfg.per_tool}, timeout={cfg.timeout_seconds}"
        )
        self._config = cfg

    def get_mode(self, tool_name: str) -> str:
        """Return execution mode for tool: always_run or ask_before_run."""
        per = self._config.per_tool or {}
        mode = per.get(tool_name, self._config.default_mode or "always_run")
        logger.info(
            f"[tool_approval] tool={tool_name}, default_mode={self._config.default_mode}, "
            f"per_tool={per}, result_mode={mode}"
        )
        return mode

    def try_resolve(self, msg: InboundMessage) -> bool:
        """If this message is a yes/no reply for a pending tool approval, resolve the future and return True."""
        key = msg.session_key
        future = self._pending_approvals.get(key)
        if future is None or future.done():
            logger.debug(f"[tool_approval] No pending approval for key={key}")
            return False

        content = (msg.content or "").strip().lower()
        first_word = content.split()[0] if content.split() else ""
        logger.info(
            f"[tool_approval] Checking approval response: key={key}, content={content!r}, first_word={first_word!r}"
        )

        if first_word in ("yes", "y", "approve", "allow", "ok"):
            logger.info(f"[tool_approval] Approved by user for key={key}")
            future.set_result(True)
            self._pending_approvals.pop(key, None)
            return True
        if first_word in ("no", "n", "reject", "deny"):
            logger.info(f"[tool_approval] Denied by user for key={key}")
            future.set_result(False)
            self._pending_approvals.pop(key, None)
            return True
        logger.debug(f"[tool_approval] Content not recognized as approval/denial: {content!r}")
        return False

    async def request_approval(self, tool_call: Any, channel: str, chat_id: str) -> bool:
        """Send approval prompt to the user in-channel and wait for yes/no. Returns True if approved."""
        args_preview = json.dumps(tool_call.arguments, ensure_ascii=False)
        if len(args_preview) > 80:
            args_preview = args_preview[:77] + "..."
        prompt = (
            f"I want to run **{tool_call.name}** with arguments: `{args_preview}`. "
            "Approve? Reply **yes** or **no**."
        )
        await self._bus.publish_outbound(
            OutboundMessage(channel=channel, chat_id=chat_id, content=prompt)
        )
        session_key = f"{channel}:{chat_id}"
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self._pending_approvals[session_key] = future
        timeout = self._config.timeout_seconds or 120
        logger.info(f"[tool_approval] Waiting for approval: key={session_key}, timeout={timeout}s")

        async def _consume_until_resolved() -> None:
            """Consume messages from bus and check for approval while main loop is blocked."""
            while not future.done():
                try:
                    msg = await asyncio.wait_for(self._bus.consume_inbound(), timeout=1.0)
                    if self.try_resolve(msg):
                        logger.info("[tool_approval] Resolved approval from background consumer")
                    else:
                        await self._bus.publish_inbound(msg)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break

        consumer_task = asyncio.create_task(_consume_until_resolved())
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"[tool_approval] Approval timed out for key={session_key}")
            self._pending_approvals.pop(session_key, None)
            return False
        finally:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
            self._pending_approvals.pop(session_key, None)
