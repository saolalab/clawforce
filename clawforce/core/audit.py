"""Security audit logging: auth and secrets access events."""

import logging
from datetime import datetime, timezone

audit_logger = logging.getLogger("clawforce.audit")


def log_auth_event(
    event: str,
    user_id: str | None,
    ip: str,
    success: bool,
    detail: str = "",
) -> None:
    """Log an authentication event (e.g. login success/failure)."""
    audit_logger.info(
        "auth_event",
        extra={
            "event": event,
            "user_id": user_id,
            "ip": ip,
            "success": success,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def log_agent_config_fetch(agent_id: str, ip: str, success: bool, detail: str = "") -> None:
    """Log when an agent fetches its config (includes secrets) during bootstrap."""
    audit_logger.info(
        "agent_config_fetch",
        extra={
            "agent_id": agent_id,
            "ip": ip,
            "success": success,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
