"""LLM fault tolerance: async retry with exponential backoff."""

import asyncio
from collections.abc import Callable, Coroutine
from typing import TypeVar

T = TypeVar("T")


async def retry_async(
    func: Callable[[], Coroutine[None, None, T]],
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Run the async callable with retries. On retryable exception, wait then retry.
    After max_attempts, the last exception is raised.
    """
    wait = backoff_factor
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return await func()
        except exceptions as e:
            last_exc = e
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(wait)
            wait *= 2
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("retry_async: unreachable")
