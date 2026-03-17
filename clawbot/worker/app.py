"""Single-agent worker entry point.

Invoke with: python -m clawbot.worker.app
Requires env: AGENT_ROOT (absolute path to agent data directory).
Optional env: AGENT_ID, ADMIN_URL, AGENT_TOKEN, AGENT_LOG_LEVEL (default: INFO).
Connects to admin via WebSocket for all control plane communication.
"""

import asyncio
import os
import sys

from clawbot.core.logging import configure_logging
from clawbot.worker.lifespan import run_worker


def main() -> None:
    asyncio.run(run_worker())


def _main() -> None:
    if not os.environ.get("AGENT_ROOT"):
        print("AGENT_ROOT env var is required", file=sys.stderr)
        sys.exit(1)
    log_level = os.environ.get("AGENT_LOG_LEVEL", "INFO")
    configure_logging(log_level)
    main()


if __name__ == "__main__":
    _main()
