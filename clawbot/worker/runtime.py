"""Build the full WorkerContext from resolved paths and config."""

from pathlib import Path
from typing import Any

from clawbot.agent.agent_fs import AgentFS
from clawbot.agent.loop import AgentLoop
from clawbot.agent.runtime import make_provider
from clawbot.core.config.engine import ConfigEngine
from clawbot.core.config.sanitize import sanitize_config_for_agent
from clawbot.core.cron import CronService
from clawbot.core.heartbeat import HeartbeatService
from clawbot.core.session import SessionManager
from clawbot.core.software import SoftwareManagement
from clawbot.worker.context import WorkerContext
from clawlib.activity import ActivityEvent, ActivityLog
from clawlib.bus import InboundMessage, MessageBus
from clawlib.channels.manager import ChannelManager


def create_worker_context(
    agent_root: Path,
    config_path: Path,
    agent_id: str,
    file_service: AgentFS,
    engine: ConfigEngine | None = None,
) -> WorkerContext:
    """Load config, wire up all components, and return a single WorkerContext."""
    if engine is None:
        engine = ConfigEngine(config_path)
        engine.load()
    config = engine.full_config

    bus = MessageBus()
    provider = make_provider(config)

    workspace_path = file_service.workspace_path
    workspace_path.mkdir(parents=True, exist_ok=True)
    session_manager = SessionManager(sessions_dir=file_service.sessions_path)
    file_service.crons_path.parent.mkdir(parents=True, exist_ok=True)
    cron = CronService(file_service.crons_path)

    async def on_cron_job(job):
        """When a cron job fires, publish its message to the bus for the agent to process."""
        channel = job.payload.channel or "cli"
        chat_id = job.payload.to or "direct"
        msg = InboundMessage(
            channel=channel,
            sender_id="cron",
            chat_id=chat_id,
            content=job.payload.message,
        )
        await bus.publish_inbound(msg)
        return None

    cron.on_job = on_cron_job

    activity_log = ActivityLog(logs_path=file_service.logs_path)
    activity_log.emit(
        ActivityEvent(
            agent_id=agent_id,
            event_type="agent_started",
            channel="",
            content="Agent started",
        )
    )

    async def on_event(
        ev_type: str, channel: str, content: str, plan_id: str = "", **kwargs: Any
    ) -> None:
        activity_log.emit(
            ActivityEvent(
                agent_id=agent_id,
                event_type=ev_type,
                channel=channel,
                content=content,
                plan_id=plan_id,
                **kwargs,
            )
        )

    software_management = SoftwareManagement(
        config_path=config_path,
        workspace=file_service.workspace_path,
    )
    software_management.reload()

    engine.merge({"control_plane": {"agent_id": agent_id}})
    config = engine.full_config

    agent_loop = AgentLoop(
        bus=bus,
        provider=provider,
        file_service=file_service,
        agent_defaults=config.agents.defaults,
        tools_config=config.tools,
        control_plane=config.control_plane,
        skills_config=config.skills,
        cron_service=cron,
        session_manager=session_manager,
        software_management=software_management,
        on_event=on_event,
    )

    # Wire the agent_loop into the engine for hot-reload support
    engine._agent_loop = agent_loop

    channels = ChannelManager(config, bus, workspace=workspace_path)

    hb_cfg = config.heartbeat
    model = config.agents.defaults.model or provider.get_default_model()
    heartbeat = HeartbeatService(
        workspace=workspace_path,
        interval_s=hb_cfg.interval_s,
        cron_expr=hb_cfg.cron_expr,
        timezone=hb_cfg.timezone,
        enabled=hb_cfg.enabled,
        provider=provider,
        model=model,
    )

    # Store sanitized config on context so the agent never sees real secrets
    agent_config = sanitize_config_for_agent(config)
    cp = config.control_plane
    return WorkerContext(
        agent_id=agent_id,
        agent_root=agent_root,
        config_path=config_path,
        config=agent_config,
        engine=engine,
        agent_loop=agent_loop,
        channels=channels,
        activity_log=activity_log,
        heartbeat=heartbeat,
        cron=cron,
        file_service=file_service,
        software_management=software_management,
        admin_url=cp.admin_url if cp else "",
        agent_token=(cp.agent_token or "") if cp else "",
    )
