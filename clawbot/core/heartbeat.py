"""Heartbeat service - periodic agent wake-up to check for tasks."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine

from loguru import logger

from clawbot.core.evaluator import evaluate_response

DEFAULT_HEARTBEAT_INTERVAL_S = 30 * 60

HEARTBEAT_PROMPT = """Read .agents/HEARTBEAT.md in your workspace (if it exists).
Follow any instructions or tasks listed there."""


def _is_heartbeat_empty(content: str | None) -> bool:
    """Check if HEARTBEAT.md has no actionable content."""
    if not content:
        return True
    skip_patterns = {"- [ ]", "* [ ]", "- [x]", "* [x]"}
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("<!--") or line in skip_patterns:
            continue
        return False
    return True


def _next_cron_delay(expr: str, tz_name: str) -> float | None:
    """Return seconds until the next cron hit, or None if croniter is unavailable."""
    try:
        from zoneinfo import ZoneInfo

        from croniter import croniter
    except ImportError:
        logger.warning("Heartbeat cron_expr requires 'croniter'; falling back to interval_s")
        return None
    tz = ZoneInfo(tz_name) if tz_name else datetime.now().astimezone().tzinfo
    now = datetime.now(tz=tz)
    nxt = croniter(expr, now).get_next(datetime)
    return max(0.0, (nxt - now).total_seconds())


class HeartbeatService:
    """
    Periodic heartbeat service that wakes the agent to check for tasks.

    The agent reads .agents/HEARTBEAT.md from the workspace and executes any tasks
    listed there. If nothing needs attention, it replies HEARTBEAT_OK.

    Supports both fixed-interval and cron-expression scheduling.
    """

    def __init__(
        self,
        workspace: Path,
        on_heartbeat: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        interval_s: int = DEFAULT_HEARTBEAT_INTERVAL_S,
        cron_expr: str = "",
        timezone: str = "",
        enabled: bool = True,
        provider: Any = None,
        model: str = "",
    ):
        self.workspace = workspace
        self.on_heartbeat = on_heartbeat
        self.interval_s = interval_s
        self.cron_expr = cron_expr
        self.timezone = timezone
        self.enabled = enabled
        self._provider = provider
        self._model = model
        self._running = False
        self._task: asyncio.Task | None = None

    @property
    def heartbeat_file(self) -> Path:
        return self.workspace / ".agents" / "HEARTBEAT.md"

    def _read_heartbeat_file(self) -> str | None:
        if self.heartbeat_file.exists():
            try:
                return self.heartbeat_file.read_text()
            except Exception:
                return None
        return None

    def _next_sleep(self) -> float:
        """Compute seconds to sleep before the next tick."""
        if self.cron_expr:
            delay = _next_cron_delay(self.cron_expr, self.timezone)
            if delay is not None:
                return delay
        return float(self.interval_s)

    async def start(self) -> None:
        if not self.enabled:
            logger.info("Heartbeat disabled")
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        schedule = f"cron '{self.cron_expr}'" if self.cron_expr else f"every {self.interval_s}s"
        logger.info("Heartbeat started ({})", schedule)

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._next_sleep())
                if self._running:
                    await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error: {}", e)

    async def _tick(self) -> None:
        content = self._read_heartbeat_file()
        if _is_heartbeat_empty(content):
            logger.debug("Heartbeat: no tasks (.agents/HEARTBEAT.md empty)")
            return
        logger.info("Heartbeat: checking for tasks...")
        if self.on_heartbeat:
            try:
                response = await self.on_heartbeat(HEARTBEAT_PROMPT)
                if response and self._provider and self._model:
                    should_notify = await evaluate_response(
                        response, content or "", self._provider, self._model
                    )
                    if should_notify:
                        logger.info("Heartbeat: completed task (notifying)")
                    else:
                        logger.info("Heartbeat: silenced by post-run evaluation")
                elif response:
                    logger.info("Heartbeat: completed task")
            except Exception as e:
                logger.error("Heartbeat execution failed: {}", e)

    async def trigger_now(self) -> str | None:
        if self.on_heartbeat:
            return await self.on_heartbeat(HEARTBEAT_PROMPT)
        return None
