"""Per-agent config read/update (secrets redacted), and admin-level settings.

During provisioning/connecting, config is read from file (fallback).
Once agent is running, config is fetched via WebSocket (live).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status

from clawforce.auth import get_current_user
from clawforce.core.domain.runtime import AgentRuntimeBackend, AgentRuntimeError
from clawforce.core.secrets import global_config_redacted
from clawforce.core.storage import StorageBackend
from clawforce.core.store.agent_config import AgentConfigStore
from clawforce.core.store.agent_variables import AgentVariablesStore
from clawforce.core.store.agents import AgentStore
from clawforce.deps import (
    get_agent_config_store,
    get_agent_store,
    get_agent_variables_store,
    get_runtime,
    get_storage,
)
from clawlib.config.helpers import redact, strip_redacted
from clawlib.config.schema import ConfigUpdate

router = APIRouter(tags=["config"])

ADMIN_SETTINGS_FILE = "admin_settings.json"


def _load_admin_settings(storage: StorageBackend) -> dict:
    try:
        raw = storage.read_sync(ADMIN_SETTINGS_FILE)
        return json.loads(raw.decode("utf-8"))
    except (FileNotFoundError, Exception):
        return {}


def _config_response_persisted(config_dict: dict) -> dict:
    """Return 200 response when config was persisted to DB but agent is offline."""
    result = redact(config_dict)
    result["_meta"] = {"source": "persisted"}
    return result


@router.get("/api/agents/{agent_id}/config")
async def get_agent_config(
    agent_id: str,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Load the agent's config from AgentConfigStore (source of truth).

    When agent is online, live config can be returned via runtime.get_config;
    otherwise config is read from the database.
    """
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    runtime_status = await runtime.get_status(agent_id)
    config_dict = agent_config_store.get_config(agent_id)
    source = "store" if config_dict is not None else "default"
    if config_dict is None:
        config_dict = {}

    try:
        live = await runtime.get_config(agent_id)
        if live is not None:
            config_dict = live
            source = "live"
    except AgentRuntimeError:
        pass

    result = redact(config_dict)
    result["_meta"] = {
        "source": source,
        "agent_status": runtime_status.status,
    }
    return result


@router.put("/api/agents/{agent_id}/config")
async def put_agent_config(
    agent_id: str,
    body: ConfigUpdate,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
    agent_config_store: AgentConfigStore = Depends(get_agent_config_store),
):
    """Save config for the given agent. Persists to AgentConfigStore; pushes to agent when online."""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    clean = strip_redacted(body.model_dump(exclude_unset=True, exclude_none=True))

    persisted = agent_config_store.update_config(agent_id, clean)

    runtime_status = await runtime.get_status(agent_id)
    if runtime_status.status in ("provisioning", "connecting"):
        return _config_response_persisted(persisted)

    try:
        config_dict = await runtime.apply_config(agent_id, persisted)
    except AgentRuntimeError:
        return _config_response_persisted(persisted)
    if config_dict is None:
        return _config_response_persisted(persisted)
    # Merge channels/providers from persisted (agent returns plain only)
    for section in ("channels", "providers"):
        if section in persisted:
            config_dict = {**config_dict, section: persisted[section]}
    result = redact(config_dict)
    result["_meta"] = {"source": "live"}
    return result


@router.get("/api/agents/{agent_id}/variables")
async def get_agent_variables(
    agent_id: str,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    agent_variables_store: AgentVariablesStore = Depends(get_agent_variables_store),
):
    """Load env variables for the agent (Variables tab). Secret values are redacted."""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    variables = agent_variables_store.get_variables(agent_id, redact=True)
    return variables


@router.put("/api/agents/{agent_id}/variables")
async def put_agent_variables(
    agent_id: str,
    body: dict,
    _: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    agent_variables_store: AgentVariablesStore = Depends(get_agent_variables_store),
):
    """Save env variables for the agent. Body: { variables: {K: v}, secret_keys: [K] }. Merged; redacted (***) omitted."""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    body = body or {}
    variables = body.get("variables", body)
    if not isinstance(variables, dict):
        variables = {}
    secret_keys = frozenset(body.get("secret_keys", []))
    clean = {k: str(v) for k, v in variables.items() if k and v is not None}
    clean = {k: v for k, v in clean.items() if not (isinstance(v, str) and v.startswith("***"))}
    agent_variables_store.upsert_variables(agent_id, clean, secret_keys=secret_keys)
    return agent_variables_store.get_variables(agent_id, redact=True)


@router.get("/api/config")
async def get_global_config(_: dict = Depends(get_current_user)):
    """Return global default config (no file — just model defaults)."""
    try:
        return global_config_redacted()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/api/admin/settings")
async def get_admin_settings(
    _: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    """Load admin settings (username, password, data directory, etc.)."""
    settings = _load_admin_settings(storage)
    return redact(settings)


@router.put("/api/admin/settings")
async def put_admin_settings(
    body: dict,
    _: dict = Depends(get_current_user),
    storage: StorageBackend = Depends(get_storage),
):
    """Update admin settings (e.g., data directory path, container image).

    Allows admins to configure deployment-level settings without re-running
    the installer. Changes persist to admin_settings.json but may require
    container restart to take effect.
    """
    try:
        settings = _load_admin_settings(storage)
        # Merge updates (only allow specific keys for safety)
        allowed_keys = {"data_dir", "image", "port", "runtime_backend"}
        for key in allowed_keys:
            if key in body and body[key] is not None:
                settings[key] = body[key]
        # Persist to storage
        settings_json = json.dumps(settings, indent=2)
        storage.write_sync(ADMIN_SETTINGS_FILE, settings_json.encode("utf-8"))
        result = redact(settings)
        result["_meta"] = {"message": "Settings updated (restart container to apply changes)"}
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
