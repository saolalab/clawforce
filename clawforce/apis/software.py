"""API endpoints for the software marketplace (curated catalog and install/uninstall)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from clawforce.auth import get_current_user
from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.store.agent_config import AgentConfigStore
from clawforce.core.store.agents import AgentStore
from clawforce.deps import get_agent_config_store, get_agent_store, get_runtime
from clawlib.registry import get_software_registry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["software"])


@router.get("/api/software/catalog")
async def list_software_catalog(
    _: dict = Depends(get_current_user),
):
    """Return the curated software catalog (bundled JSON)."""
    return get_software_registry().list_entries()


@router.get("/api/software/catalog/{software_id:path}")
async def get_software_entry(
    software_id: str,
    _: dict = Depends(get_current_user),
):
    """Return a single catalog entry by id."""
    entry = get_software_registry().get_entry(software_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Software not found in catalog"
        )
    return entry


class CustomSoftwareInstallConfig(BaseModel):
    type: str = "npm"
    package: str


class CustomSoftwareRunConfig(BaseModel):
    command: str
    args: list[str] = []
    stdin: bool = False


class CustomSoftwarePostInstallConfig(BaseModel):
    """Auto-run after install/reinstall. command defaults to run.command; daemon=true runs in background."""

    command: str
    args: list[str] = []
    daemon: bool = True
    env: dict[str, str] = {}


class AddCustomSoftwareRequest(BaseModel):
    """Request body for adding a custom software entry to the catalog."""

    id: str = Field(..., description="Unique slug identifier, e.g. my-tool")
    name: str
    description: str = ""
    author: str = ""
    version: str = ""
    categories: list[str] = []
    install: CustomSoftwareInstallConfig
    run: CustomSoftwareRunConfig
    post_install: CustomSoftwarePostInstallConfig | None = None
    required_env: list[str] = []


@router.get("/api/software/custom")
async def list_custom_software(
    _: dict = Depends(get_current_user),
):
    """Return user-managed custom software entries."""
    return get_software_registry().list_custom_entries()


@router.post("/api/software/custom", status_code=status.HTTP_201_CREATED)
async def add_custom_software(
    body: AddCustomSoftwareRequest,
    _: dict = Depends(get_current_user),
):
    """Add a custom software entry to the user catalog."""
    registry = get_software_registry()
    existing = registry.get_entry(body.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Software id '{body.id}' already exists in the catalog",
        )
    entry = body.model_dump(exclude_none=True)
    registry.add_custom_entry(entry)
    return entry


@router.put("/api/software/custom/{software_id:path}", status_code=status.HTTP_200_OK)
async def update_custom_software(
    software_id: str,
    body: AddCustomSoftwareRequest,
    _: dict = Depends(get_current_user),
):
    """Update a custom software entry by id."""
    if body.id != software_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL id and body id must match",
        )
    entry = body.model_dump(exclude_none=True)
    entry["id"] = software_id
    updated = get_software_registry().update_custom_entry(software_id, entry)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom software '{software_id}' not found",
        )
    return entry


@router.delete("/api/software/custom/{software_id:path}", status_code=status.HTTP_200_OK)
async def delete_custom_software(
    software_id: str,
    _: dict = Depends(get_current_user),
):
    """Delete a custom software entry by id."""
    removed = get_software_registry().delete_custom_entry(software_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom software '{software_id}' not found",
        )
    return {"ok": True, "id": software_id}


class SoftwareInstallRequest(BaseModel):
    """Request to install a software from the catalog to an agent."""

    software_id: str
    env: dict[str, str] = {}


@router.post("/api/agents/{agent_id}/software/install")
async def install_software(
    agent_id: str,
    body: SoftwareInstallRequest,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
):
    """Install a software from the catalog into the agent (npm/pip + config). Restart agent to apply."""
    if type(runtime).__name__ == "LocalRuntime":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Software installation is only available in k8s pod mode. "
            "Switch to k8s runtime backend first.",
        )
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    runtime_status = await runtime.get_status(agent_id)
    if runtime_status.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent is not running (status: {runtime_status.status}). Start the agent first.",
        )

    entry = get_software_registry().get_entry(body.software_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Software '{body.software_id}' not found in catalog",
        )

    install_cfg = entry.get("install") or {}
    run_cfg = entry.get("run") or {}
    install_type = install_cfg.get("type", "npm")
    package = install_cfg.get("package", "")
    if not package:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Catalog entry has no install.package"
        )

    command = run_cfg.get("command", "")
    args = run_cfg.get("args") or []
    stdin = bool(run_cfg.get("stdin", False))
    post_install = entry.get("post_install")

    try:
        result = await runtime.install_software(
            agent_id=agent_id,
            slug=body.software_id,
            package=package,
            install_type=install_type,
            name=entry.get("name", ""),
            description=entry.get("description", ""),
            skill_content=entry.get("skill_content", ""),
            command=command,
            args=args,
            stdin=stdin,
            env=body.env,
            post_install=post_install,
        )
    except Exception as e:
        logger.exception("Failed to install software")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Install failed: {e!s}"
        ) from e

    if result.get("ok"):
        try:
            live_config = await runtime.get_config(agent_id)
            if live_config and live_config.get("tools", {}).get("software"):
                agent_config_store.update_config(
                    agent_id,
                    {"tools": {"software": live_config["tools"]["software"]}},
                    replace_keys=[("tools", "software")],
                )
        except Exception as sync_err:
            logger.warning("Failed to sync software config to store: %s", sync_err)

    return {
        "ok": result.get("ok", True),
        "slug": result.get("slug", body.software_id),
        "message": result.get("message", "Installed. Restart the agent to apply."),
        "logs": result.get("logs", ""),
        "exit_code": result.get("exit_code", 0),
        "verified": result.get("verified", False),
    }


class SoftwareUninstallRequest(BaseModel):
    """Request to uninstall a software from an agent."""

    slug: str


@router.post("/api/agents/{agent_id}/software/uninstall")
async def uninstall_software(
    agent_id: str,
    body: SoftwareUninstallRequest,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
):
    """Uninstall a software from the agent (npm/pip uninstall + remove from config)."""
    if type(runtime).__name__ == "LocalRuntime":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Software uninstallation is only available in k8s pod mode. "
            "Switch to k8s runtime backend first.",
        )
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    runtime_status = await runtime.get_status(agent_id)
    if runtime_status.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent is not running (status: {runtime_status.status}). Start the agent first.",
        )

    try:
        result = await runtime.uninstall_software(agent_id=agent_id, slug=body.slug)
    except Exception as e:
        logger.exception("Failed to uninstall software")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Uninstall failed: {e!s}"
        ) from e

    if result.get("ok"):
        try:
            live_config = await runtime.get_config(agent_id)
            if live_config is not None:
                agent_config_store.update_config(
                    agent_id,
                    {"tools": {"software": live_config.get("tools", {}).get("software", {})}},
                    replace_keys=[("tools", "software")],
                )
        except Exception as sync_err:
            logger.warning("Failed to sync software config to store: %s", sync_err)

    return {
        "ok": True,
        "slug": result.get("slug", body.slug),
        "message": result.get("message", "Uninstalled."),
    }
