"""Config handlers for reading and updating configuration.

Uses long-lived ConfigEngine from WorkerContext (no disk re-read on each call).
Config includes both plain settings and secret sections (providers, channels).
Env variables are injected by the runtime at spawn from AgentVariablesStore.
"""

import asyncio

from clawbot.core.config.engine import ConfigEngine
from clawbot.worker.context import WorkerContext
from clawbot.worker.handlers.schema import PutConfigRequest
from clawlib.config.loader import deep_merge
from clawlib.config.schema import Config


def handle_get_config(engine: ConfigEngine) -> dict:
    """Return config domain from engine."""
    return {"data": engine.config_dict()}


async def handle_put_config(engine: ConfigEngine, req: PutConfigRequest) -> dict:
    """Update config domain via engine and hot-reload (approval + MCP)."""
    updated = await engine.apply_update(req.body)
    return {"data": updated}


async def handle_apply_config(ctx: WorkerContext, body: dict) -> dict:
    """Apply a full configuration blob (including secret sections) and refresh runtime.

    Merges body into the engine, injects env, updates provider secrets on the agent
    loop, and restarts the channel manager so all config (e.g. Slack tokens) takes effect.
    """
    if not body:
        return {"ok": True}
    engine = ctx.engine
    engine.merge(body)
    engine.inject_to_env()  # providers/channels: next subprocess / os.environ read sees new values

    # Providers: agent loop can swap API keys in memory via update_provider_secrets (no restart).
    providers = engine.secrets_dict().get("providers") or {}
    if providers and hasattr(ctx.agent_loop, "update_provider_secrets"):
        ctx.agent_loop.update_provider_secrets(providers)

    # Channels: no per-channel "reload credentials" API; they hold live connections, so restart with new config.
    await ctx.channels.stop_all()
    full_dict = deep_merge(
        engine.full_config.model_dump(by_alias=False),
        {"control_plane": ctx.config.control_plane.model_dump(by_alias=False)}
        if ctx.config and ctx.config.control_plane
        else {},
    )
    ctx.channels.set_config(Config.model_validate(full_dict))
    asyncio.create_task(ctx.channels.start_all())
    return {"ok": True}
