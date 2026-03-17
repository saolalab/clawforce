"""WorkerContext: single object carrying all worker runtime components."""

from dataclasses import dataclass
from pathlib import Path

from clawbot.agent.agent_fs import AgentFS
from clawbot.agent.loop import AgentLoop
from clawbot.core.config.engine import ConfigEngine
from clawbot.core.config.schema import Config
from clawbot.core.cron import CronService
from clawbot.core.heartbeat import HeartbeatService
from clawbot.core.software import SoftwareManagement
from clawlib.activity import ActivityLog
from clawlib.channels.manager import ChannelManager


@dataclass(slots=True)
class WorkerContext:
    """Immutable bundle for one agent instance (data-plane runtime; one worker = one agent).

    config is always sanitized (secret values replaced by placeholder) so the
    agent and any agent-visible code never see real credentials.
    engine is long-lived so get_config/put_config use it directly (no disk re-read).
    admin_url and agent_token are for the admin WebSocket client only (not in config).
    """

    agent_id: str
    agent_root: Path
    config_path: Path
    config: Config
    engine: ConfigEngine
    agent_loop: AgentLoop
    channels: ChannelManager
    activity_log: ActivityLog
    heartbeat: HeartbeatService
    cron: CronService
    file_service: AgentFS
    software_management: SoftwareManagement
    admin_url: str = ""
    agent_token: str = ""
