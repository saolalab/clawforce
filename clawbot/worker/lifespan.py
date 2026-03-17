"""Worker lifecycle: resolve → provision → build context → run until signal."""

import asyncio
import os
import signal

from loguru import logger

from clawbot.core.admin import AdminClient
from clawbot.core.config.engine import ConfigEngine
from clawbot.core.connection_config import SOFTWARE_REINSTALL_DELAY_S
from clawbot.worker.context import WorkerContext
from clawbot.worker.provision import provision_agent_root
from clawbot.worker.resolve import resolve_agent_root
from clawbot.worker.runtime import create_worker_context

# Global state for software installation status (checked by health handler)
_software_installing: bool = False


def is_software_installing() -> bool:
    """Check if software is being installed in background. Used by health handler."""
    return _software_installing


async def run_worker() -> None:
    """Boot the worker, connect to admin, and block until SIGINT/SIGTERM.

    Bootstrap fetches config and secrets over WS when ADMIN_URL and AGENT_TOKEN are set.
    """
    ctx, admin_client = await _build_context()
    stop = _install_signal_handlers()

    admin_task = (
        asyncio.create_task(admin_client.run_with_reconnect(stop)) if admin_client else None
    )

    software_task = asyncio.create_task(_deferred_software_reinstall(ctx.software_management))

    agent_task = asyncio.create_task(_run_agent(ctx))
    await ctx.heartbeat.start()
    await ctx.cron.start()

    logger.info("Worker running (agent_id={}). Waiting for shutdown signal...", ctx.agent_id)
    await stop.wait()
    logger.info("Shutdown signal received, stopping worker...")

    software_task.cancel()
    await _shutdown(ctx, agent_task, admin_task, admin_client)


# -- Boot phases --------------------------------------------------------------


def _apply_envs() -> tuple[str, str]:
    """Read ADMIN_URL and AGENT_TOKEN from environment. Returns (admin_url, agent_token)."""
    admin_url = os.environ.get("ADMIN_URL") or os.environ.get("ADMIN_PUBLIC_URL", "")
    agent_token = os.environ.get("AGENT_TOKEN", "")
    return (admin_url, agent_token)


async def _build_context() -> tuple[WorkerContext, AdminClient | None]:
    """Resolve paths, provision, load config + secrets (WS or file), build runtime.

    When ADMIN_URL and AGENT_TOKEN are set, connects to admin over WS and fetches
    secrets and config during bootstrap. Otherwise falls back to local files only.
    Returns (ctx, admin_client) so the caller can start client.run() after context is built.
    """
    agent_root, config_path, agent_id, file_service = resolve_agent_root()
    if not (agent_root / ".config").exists():
        provision_agent_root(agent_root, agent_id)

    admin_url, agent_token = _apply_envs()
    engine = ConfigEngine(config_path)
    admin_client: AdminClient | None = None

    if admin_url and agent_token:
        logger.info(f"Bootstrap: connecting to admin at {admin_url}")
        try:
            admin_client = AdminClient(
                admin_url=admin_url,
                agent_token=agent_token,
                agent_id=agent_id,
            )
            await admin_client.connect()
            logger.info("Bootstrap: connected to admin, fetching config")
            await admin_client.report_status(
                {"status": "bootstrapping", "phase": "fetching_config"}
            )
            admin_config = await admin_client.get_config()
            engine.load(admin_blob=admin_config)
            engine.inject_to_env()
            logger.info("Bootstrap: config loaded, control plane ready")
        except Exception as e:
            logger.error(
                "Bootstrap from admin failed (ADMIN_URL=%s): %s. "
                "In managed mode, the agent must connect to the control plane.",
                admin_url,
                e,
            )
            admin_client = None
    else:
        logger.info("No control plane configured, using local config only")
        engine.load()
        engine.inject_to_env()

    if admin_url or agent_token:
        engine.merge(
            {
                "control_plane": {
                    "agent_id": agent_id,
                    "admin_url": admin_url,
                    "agent_token": agent_token,
                }
            }
        )

    ctx = create_worker_context(agent_root, config_path, agent_id, file_service, engine=engine)

    if admin_client:
        admin_client.set_context(ctx)
        await admin_client.report_status({"status": "running"})

    return (ctx, admin_client)


# -- Software re-installation -------------------------------------------------


async def _deferred_software_reinstall(software_management) -> None:
    """Run software reinstall in background after WebSocket connects.

    Waits SOFTWARE_REINSTALL_DELAY_S to let the connection establish first.
    Software reinstall can take minutes for npm/pip packages.

    Sets global _software_installing flag so health endpoint reports status.
    """
    global _software_installing
    try:
        await asyncio.sleep(SOFTWARE_REINSTALL_DELAY_S)
        _software_installing = True
        logger.info("Starting background software reinstall...")
        await software_management.reinstall_missing()
        logger.info("Background software reinstall completed")
    except asyncio.CancelledError:
        logger.debug("Software reinstall task cancelled during shutdown")
    except Exception as e:
        logger.error(f"Background software reinstall failed: {e}")
    finally:
        _software_installing = False


# -- Running phases -----------------------------------------------------------


def _install_signal_handlers() -> asyncio.Event:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    return stop


async def _run_agent(ctx: WorkerContext) -> None:
    """Run the agent loop and channels; clean up on exit."""
    ctx.heartbeat.on_heartbeat = lambda prompt: ctx.agent_loop.process_direct(
        prompt,
        session_key="system:heartbeat",
        channel="system",
        chat_id="heartbeat",
    )
    try:
        await asyncio.gather(ctx.agent_loop.run(), ctx.channels.start_all())
    except asyncio.CancelledError:
        pass
    except BaseException as e:
        logger.error("run_agent: unexpected {}: {}", type(e).__name__, e)
        raise
    finally:
        await ctx.agent_loop.close_mcp()
        ctx.agent_loop.stop()
        await ctx.channels.stop_all()


# -- Shutdown -----------------------------------------------------------------


async def _shutdown(
    ctx: WorkerContext,
    agent_task: asyncio.Task,
    admin_task: asyncio.Task | None,
    admin_client: AdminClient | None,
) -> None:
    ctx.heartbeat.stop()
    ctx.cron.stop()
    agent_task.cancel()
    try:
        await asyncio.wait_for(asyncio.shield(agent_task), timeout=5.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    if admin_client:
        await admin_client.stop()
    if admin_task:
        admin_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(admin_task), timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
