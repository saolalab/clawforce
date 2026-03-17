"""Control plane WebSocket hub: agents connect and register, push activity, receive messages.

Protocol:
  - Agent sends {type: register, agent_id, token}
  - Admin validates, sets store status="running", responds {type: registered, ok: true}
  - On disconnect (any cause): admin sets store status="stopped"
  - Agent may send {type: status, status: {...}} to update store (e.g. bootstrapping)
"""

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel

from clawforce.auth import get_current_user
from clawforce.core.acp import RunStore
from clawforce.core.audit import log_agent_config_fetch
from clawforce.core.database import get_database
from clawforce.core.domain.agent import control_plane_overrides
from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.runtimes.factory import RUNTIME_BACKENDS, get_runtime_backend
from clawforce.core.storage import StorageBackend, get_storage_root
from clawforce.core.store.agent_config import AgentConfigStore
from clawforce.core.store.agents import AgentStore
from clawforce.deps import _get_fernet, get_runtime, get_storage
from clawlib.activity import ActivityEvent, ActivityLogRegistry

router = APIRouter(tags=["control"])


RUNTIME_LABELS: dict[str, str] = {
    "process": "Process (one subprocess per agent — default)",
    "docker": "Docker (one container per agent — full isolation)",
}


@router.get("/api/runtime/info")
async def runtime_info(
    _: dict = Depends(get_current_user),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
    storage: StorageBackend = Depends(get_storage),
):
    """Return current runtime backend type, running agents, and available backends."""
    runtime_cls = type(runtime).__name__
    kind = {
        "LocalRuntime": "process",
        "DockerRuntime": "docker",
    }.get(runtime_cls, runtime_cls)
    running_ids = runtime.running_agent_ids() if hasattr(runtime, "running_agent_ids") else []
    root = get_storage_root(storage)
    out = {
        "runtime_type": kind,
        "runtime_label": RUNTIME_LABELS.get(kind, kind),
        "running_count": len(running_ids),
        "running_agent_ids": running_ids,
        "available_backends": [
            {"value": k, "label": RUNTIME_LABELS.get(k, k)} for k in RUNTIME_BACKENDS
        ],
        "data_root": str(root) if root else None,
    }
    if hasattr(runtime, "get_docker_presets"):
        out["docker_presets"] = runtime.get_docker_presets()
    return out


class RuntimeBackendUpdate(BaseModel):
    runtime_type: str


@router.put("/api/runtime/backend")
async def set_runtime_backend(
    body: RuntimeBackendUpdate,
    request: Request,
    _: dict = Depends(get_current_user),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Switch the runtime backend. Stops all running agents first."""
    kind = body.runtime_type.lower()
    if kind not in RUNTIME_BACKENDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown backend: {kind}. Choose from: {list(RUNTIME_BACKENDS)}",
        )
    running_ids = runtime.running_agent_ids() if hasattr(runtime, "running_agent_ids") else []
    if running_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot switch backend while {len(running_ids)} agent(s) are running. "
            "Stop all agents first.",
        )
    new_runtime = get_runtime_backend(
        kind=kind,
        storage=request.app.state.storage,
        ws_manager=request.app.state.ws_manager,
        activity_registry=request.app.state.activity_registry,
    )
    request.app.state.runtime = new_runtime
    return {"ok": True, "runtime_type": kind, "runtime_label": RUNTIME_LABELS.get(kind, kind)}


@router.websocket("/api/control/ws")
async def control_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    agent_id: str | None = None
    app = websocket.app
    storage = getattr(app.state, "storage", None)
    activity_registry: ActivityLogRegistry | None = getattr(app.state, "activity_registry", None)
    activity_events_store = getattr(app.state, "activity_events_store", None)
    manager = getattr(app.state, "ws_manager", None)
    run_store: RunStore | None = getattr(app.state, "run_store", None)
    if storage is None or activity_registry is None or manager is None or run_store is None:
        await websocket.close(code=4510)
        return
    store = AgentStore(get_database(), storage)
    try:
        msg = await websocket.receive_json()
        if msg.get("type") != "register":
            await websocket.close(code=4001)
            return
        agent_id = msg.get("agent_id") or ""
        token = msg.get("token") or ""
        if not agent_id:
            await websocket.close(code=4002)
            return
        agent = store.get_agent(agent_id)
        if not agent or not agent.enabled:
            await websocket.close(code=4003)
            return
        if not token or not agent.agent_token or agent.agent_token != token:
            await websocket.close(code=4004)
            return
        manager.register(agent_id, websocket)
        store.update_agent(agent_id, status="running")
        logging.getLogger(__name__).info("Agent %s registered (WebSocket connected)", agent_id)
        await websocket.send_json({"type": "registered", "ok": True})

        agent_config_store = AgentConfigStore(get_database(), fernet=_get_fernet())
        agent = store.get_agent(agent_id)

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "heartbeat":
                pass
            elif msg_type == "request":
                request_id = data.get("request_id", "")
                action = data.get("action", "")
                try:
                    if action == "get_config":
                        config = agent_config_store.get_config(agent_id) or {}
                        if agent:
                            config = {**config, "control_plane": control_plane_overrides(agent)}
                        client_ip = websocket.client.host if websocket.client else "unknown"
                        log_agent_config_fetch(agent_id, ip=client_ip, success=True)
                        await websocket.send_json(
                            {
                                "type": "response",
                                "request_id": request_id,
                                "ok": True,
                                "data": config,
                            }
                        )
                    else:
                        await websocket.send_json(
                            {
                                "type": "response",
                                "request_id": request_id,
                                "ok": False,
                                "error": f"Unknown action: {action}",
                            }
                        )
                except Exception as e:
                    await websocket.send_json(
                        {
                            "type": "response",
                            "request_id": request_id,
                            "ok": False,
                            "error": str(e),
                        }
                    )
            elif msg_type == "response":
                request_id = data.get("request_id")
                if request_id:
                    manager.resolve_response(request_id, data)
            elif msg_type == "status":
                status_payload = data.get("status") or {}
                if isinstance(status_payload, dict):
                    new_status = status_payload.get("status")
                    if new_status in (
                        "provisioning",
                        "connecting",
                        "bootstrapping",
                        "running",
                        "stopped",
                        "error",
                    ):
                        store.update_agent(agent_id, status=new_status)
            elif msg_type == "acp_run_result":
                run_id = data.get("run_id", "")
                content = data.get("content", "")
                error = data.get("error")
                if error:
                    run_store.reject(run_id, error)
                else:
                    run_store.resolve(run_id, content=content)
            elif msg_type == "activity":
                events = data.get("events") or []
                log = activity_registry.get_or_create(agent_id)
                for e in events:
                    ev = ActivityEvent(
                        agent_id=e.get("agent_id", agent_id),
                        event_type=e.get("event_type", ""),
                        channel=e.get("channel", ""),
                        content=e.get("content", ""),
                        plan_id=e.get("plan_id", ""),
                        timestamp=e.get("timestamp", ""),
                        tool_name=e.get("tool_name"),
                        result_status=e.get("result_status"),
                        duration_ms=e.get("duration_ms"),
                        event_id=e.get("event_id"),
                    )
                    inserted = True
                    if activity_events_store:
                        inserted = activity_events_store.insert(ev)
                    if inserted:
                        log.emit(ev)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if agent_id:
            logging.getLogger(__name__).info("Agent %s disconnected", agent_id)
            manager.disconnect(agent_id)
            if storage and store:
                store.update_agent(agent_id, status="stopped")
