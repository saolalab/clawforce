"""Software handlers for installing and uninstalling software via SoftwareManagement."""

from clawbot.agent.loop import AgentLoop
from clawbot.core.config.engine import ConfigEngine
from clawbot.worker.handlers.schema import (
    InstallSoftwareRequest,
    UninstallSoftwareRequest,
)


async def handle_install_software(
    agent_loop: AgentLoop, req: InstallSoftwareRequest, *, engine: ConfigEngine | None = None
) -> dict:
    mgmt = agent_loop.software_management
    if not mgmt:
        return {
            "data": {
                "ok": False,
                "slug": req.slug,
                "message": "Software management not available",
            }
        }
    payload = {k: v for k, v in req.model_dump().items() if k != "action"}
    result = await mgmt.install(**payload)
    if result.get("ok") and engine:
        engine.load()
    return {"data": result}


async def handle_uninstall_software(
    agent_loop: AgentLoop, req: UninstallSoftwareRequest, *, engine: ConfigEngine | None = None
) -> dict:
    mgmt = agent_loop.software_management
    if not mgmt:
        return {
            "data": {
                "ok": False,
                "slug": req.slug,
                "message": "Software management not available",
            }
        }
    try:
        result = await mgmt.uninstall(req.slug)
        if result.get("ok") and engine:
            engine.load()
        return {"data": result}
    except (FileNotFoundError, ValueError) as e:
        return {"data": {"ok": False, "slug": req.slug, "message": str(e)}}
