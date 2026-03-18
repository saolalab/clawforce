"""Agent CRUD and lifecycle endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from clawforce.auth import get_current_user
from clawforce.core.authz import can_access_agent, require_agent_access
from clawforce.core.domain.runtime import AgentRuntimeBackend, AgentRuntimeError
from clawforce.core.store.agent_config import AgentConfigStore
from clawforce.core.store.agent_variables import AgentVariablesStore, default_git_variables
from clawforce.core.store.agents import AgentStore
from clawforce.deps import (
    get_agent_config_store,
    get_agent_store,
    get_agent_variables_store,
    get_runtime,
)
from clawlib.config.helpers import redact, strip_redacted, validate_channels
from clawlib.config.schema import ChannelsConfig

from ._schemas import AgentCreate, AgentUpdate

logger = logging.getLogger(__name__)


def _agent_response(agent, config_dict: dict | None) -> dict:
    """Build a redacted agent response, merging live config when available."""
    if config_dict is None:
        return redact({**agent.model_dump()})
    out = {**agent.model_dump()}
    out.update(config_dict.get("agents", {}).get("defaults") or {})
    out["channels"] = config_dict.get("channels") or {}
    out["providers"] = config_dict.get("providers") or {}
    out["tools"] = config_dict.get("tools") or {}
    out["skills"] = config_dict.get("skills") or {}
    out["heartbeat"] = config_dict.get("heartbeat") or {}
    out["security"] = config_dict.get("security") or {}
    return redact(out)


router = APIRouter(tags=["agents"])


def _build_update_overrides(
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    max_tool_iterations: int | None = None,
    memory_window: int | None = None,
    fault_tolerance: dict | None = None,
    channels: ChannelsConfig | dict | None = None,
    providers: dict | None = None,
    tools: dict | None = None,
    skills: dict | None = None,
    heartbeat: dict | None = None,
    security: dict | None = None,
) -> dict:
    """Build config overrides from update-agent fields. Only non-None fields included."""
    overrides: dict = {}
    defaults: dict = {}
    if model is not None:
        defaults["model"] = model
    if temperature is not None:
        defaults["temperature"] = temperature
    if max_tokens is not None:
        defaults["max_tokens"] = max_tokens
    if max_tool_iterations is not None:
        defaults["max_tool_iterations"] = max_tool_iterations
    if memory_window is not None:
        defaults["memory_window"] = memory_window
    if fault_tolerance is not None:
        defaults["fault_tolerance"] = fault_tolerance
    if defaults:
        overrides["agents"] = {"defaults": defaults}
    if channels is not None:
        overrides["channels"] = (
            channels.model_dump(by_alias=False)
            if isinstance(channels, ChannelsConfig)
            else validate_channels(channels)
        )
    if providers is not None:
        overrides["providers"] = providers
    if tools is not None:
        overrides["tools"] = tools
    if skills is not None:
        overrides["skills"] = skills
    if heartbeat is not None:
        overrides["heartbeat"] = heartbeat
    if security is not None:
        overrides["security"] = security
    return overrides


@router.get("/api/agents")
async def list_all_agents(
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    agents = store.list_agents()
    accessible = [a for a in agents if can_access_agent(current, a)]
    result = []
    for a in accessible:
        runtime_status = await runtime.get_status(a.id)
        agent_dict = redact(a.model_dump())
        agent_dict["status"] = runtime_status.status
        if runtime_status.message:
            agent_dict["status_message"] = runtime_status.message
        config = agent_config_store.get_config(a.id) or {}
        channels = config.get("channels") or {}
        agent_dict["channels_enabled"] = [
            ch for ch, cfg in channels.items() if isinstance(cfg, dict) and cfg.get("enabled")
        ]
        result.append(agent_dict)
    return result


@router.post("/api/agents")
async def create_agent_flat(
    body: AgentCreate,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    variables_store: AgentVariablesStore = Depends(get_agent_variables_store),
):
    a = store.create_agent(
        name=body.name,
        owner_user_id=current.get("id", ""),
        description=body.description,
        provision=True,
        template=body.template,
        mode=body.mode,
        color=body.color,
    )
    variables_store.upsert_variables(a.id, default_git_variables(a.name), secret_keys=frozenset())
    return _agent_response(a, None)


@router.get("/api/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    a = store.get_agent(agent_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, a)
    runtime_status = await runtime.get_status(agent_id)
    try:
        config_dict = await runtime.get_config(agent_id)
    except AgentRuntimeError:
        config_dict = None
    if config_dict is None:
        # get_config returns full config (plain + resolved secrets) from the store
        config_dict = agent_config_store.get_config(agent_id) or {}
    else:
        # Agent's config_dict excludes channels/providers (SECRET_SECTIONS).
        # Merge them from the store so the UI shows the correct enabled state.
        store_config = agent_config_store.get_config(agent_id) or {}
        for section in ("channels", "providers"):
            if section in store_config:
                config_dict = {**config_dict, section: store_config[section]}
    resp = _agent_response(a, config_dict)
    resp["status"] = runtime_status.status
    if runtime_status.message:
        resp["status_message"] = runtime_status.message
    if runtime_status.mcp:
        resp["mcp_status"] = runtime_status.mcp
    if runtime_status.software_warnings:
        resp["software_warnings"] = runtime_status.software_warnings
    if runtime_status.software_installing:
        resp["software_installing"] = True
    return resp


@router.put("/api/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    store_only = {
        k: v
        for k, v in body.model_dump(exclude_unset=True).items()
        if k in ("name", "description", "enabled", "color", "mode", "onboarding_completed")
    }
    a = store.update_agent(agent_id, **store_only) if store_only else store.get_agent(agent_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, a)

    overrides = _build_update_overrides(
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        max_tool_iterations=body.max_tool_iterations,
        memory_window=body.memory_window,
        fault_tolerance=body.fault_tolerance,
        channels=body.channels,
        providers=body.providers,
        tools=body.tools,
        skills=body.skills,
        heartbeat=body.heartbeat,
        security=body.security,
    )
    config_dict = None
    if overrides:
        overrides = strip_redacted(overrides)
        replace_keys = [("tools", "mcp_servers")] if body.tools and "mcp_servers" in body.tools else None
        persisted = agent_config_store.update_config(agent_id, overrides, replace_keys=replace_keys)
        try:
            config_dict = await runtime.apply_config(agent_id, persisted)
        except AgentRuntimeError:
            config_dict = persisted
        if config_dict is None:
            config_dict = persisted
    if config_dict is None:
        try:
            config_dict = await runtime.get_config(agent_id)
        except AgentRuntimeError:
            config_dict = None
        if config_dict is None:
            config_dict = agent_config_store.get_config(agent_id) or {}
    # Merge channels/providers from store so UI has correct state (agent returns plain only)
    store_config = agent_config_store.get_config(agent_id) or {}
    for section in ("channels", "providers"):
        if section in store_config:
            config_dict = {**config_dict, section: store_config[section]}
    return _agent_response(a, config_dict)


@router.delete("/api/agents/{agent_id}")
def delete_agent(
    agent_id: str,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
):
    a = store.get_agent(agent_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, a)
    if not store.delete_agent(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return {"ok": True}


@router.post("/api/agents/{agent_id}/start")
async def start_agent(
    agent_id: str,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    a = store.get_agent(agent_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, a)
    try:
        await runtime.start_agent(agent_id)
    except AgentRuntimeError as exc:
        logger.warning(f"Failed to start agent {agent_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(f"Failed to start agent {agent_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    return {"ok": True, "status": "running"}


@router.post("/api/agents/{agent_id}/stop")
async def stop_agent(
    agent_id: str,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    a = store.get_agent(agent_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, a)
    try:
        await runtime.stop_agent(agent_id)
    except AgentRuntimeError as exc:
        logger.warning(f"Failed to stop agent {agent_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"ok": True, "status": "stopped"}


@router.get("/api/agents/{agent_id}/status")
async def agent_status(
    agent_id: str,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    a = store.get_agent(agent_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, a)
    runtime_status = await runtime.get_status(agent_id)
    return {"agent_id": runtime_status.agent_id, "status": runtime_status.status}
