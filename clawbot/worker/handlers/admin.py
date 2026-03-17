"""Admin request handlers — business logic for the worker ↔ admin protocol.

Each handler receives typed schema models and the specific dependencies it
needs.  No transport / WebSocket awareness.  Pure logic → return data or raise.
"""

import os
import shutil
from typing import Any

from clawbot.agent.agent_fs import AgentFS
from clawbot.agent.loop import AgentLoop
from clawbot.core.config.engine import ConfigEngine
from clawbot.worker.context import WorkerContext
from clawbot.worker.handlers.config import (
    handle_apply_config,
    handle_get_config,
    handle_put_config,
)
from clawbot.worker.handlers.filesystem import (
    handle_create_folder,
    handle_delete_file,
    handle_list_workspace,
    handle_move_file,
    handle_read_file,
    handle_rename_file,
    handle_upload_file,
    handle_write_file,
)
from clawbot.worker.handlers.schema import (
    ActivityEventPayload,
    CreateFolderRequest,
    DeleteFileRequest,
    GetActivityRequest,
    HealthData,
    InstallSkillRequest,
    InstallSoftwareRequest,
    ListWorkspaceRequest,
    MoveFileRequest,
    PutConfigRequest,
    ReadFileRequest,
    RenameFileRequest,
    SoftwareWarning,
    UninstallSkillRequest,
    UninstallSoftwareRequest,
    UploadFileRequest,
    WriteFileRequest,
)
from clawbot.worker.handlers.skill import (
    handle_install_skill,
    handle_uninstall_skill,
)
from clawbot.worker.handlers.software import (
    handle_install_software,
    handle_uninstall_software,
)
from clawlib.activity import ActivityLog

# -- Simple handlers (health, activity, config) --------------------------------


def _check_software_warnings(software: dict[str, Any]) -> list[SoftwareWarning] | None:
    """Return warnings for installed software whose binary is missing from PATH."""
    warnings: list[SoftwareWarning] = []
    for key, entry in software.items():
        if isinstance(entry, dict):
            command = entry.get("command", "")
            name = entry.get("name", "") or key
        else:
            command = getattr(entry, "command", "")
            name = getattr(entry, "name", "") or key
        if not command:
            continue
        if os.path.isabs(command):
            if not (os.path.isfile(command) and os.access(command, os.X_OK)):
                warnings.append(SoftwareWarning(key=key, name=name, command=command))
        elif not shutil.which(command):
            warnings.append(SoftwareWarning(key=key, name=name, command=command))
    return warnings or None


def handle_get_health(agent_loop: AgentLoop) -> dict:
    from clawbot.worker.lifespan import is_software_installing

    mcp: dict[str, Any] | None = None
    if agent_loop.mcp_status:
        mcp = {name: s.to_dict() for name, s in agent_loop.mcp_status.items()}
    catalog = agent_loop.software_management.get_catalog() if agent_loop.software_management else {}
    sw_warnings = _check_software_warnings(catalog)
    sw_installing = is_software_installing()
    return {
        "data": HealthData(
            status="ok",
            mcp=mcp,
            software_warnings=sw_warnings,
            software_installing=sw_installing,
        ).model_dump(exclude_none=True)
    }


def handle_get_activity(activity_log: ActivityLog, req: GetActivityRequest) -> dict:
    events = activity_log.recent(req.limit)
    return {
        "data": [
            ActivityEventPayload(
                agent_id=e.agent_id,
                event_type=e.event_type,
                channel=e.channel,
                content=e.content,
                timestamp=e.timestamp,
                tool_name=e.tool_name,
                result_status=e.result_status,
                duration_ms=e.duration_ms,
            ).model_dump(exclude_none=True)
            for e in events
        ]
    }


def handle_get_mcp_tools(agent_loop: AgentLoop, server_key: str) -> dict:
    """Get list of tools provided by an MCP server."""
    mcp_registry = agent_loop.mcp
    if not mcp_registry:
        return {"ok": False, "error": "MCP registry not available"}

    # Get all tools and filter by server prefix
    all_tools = mcp_registry.get_definitions()
    server_prefix = f"mcp_{server_key}_"

    server_tools = []
    for tool_def in all_tools:
        if tool_def.get("name", "").startswith(server_prefix):
            # Extract the tool name without the prefix
            original_name = tool_def.get("name", "")[len(server_prefix) :]
            server_tools.append(
                {
                    "name": original_name,
                    "full_name": tool_def.get("name", ""),
                    "description": tool_def.get("description", ""),
                    "parameters": tool_def.get("parameters", {}),
                }
            )

    return {
        "ok": True,
        "data": {"tools": server_tools},
    }


# -- Dispatcher ---------------------------------------------------------------


async def dispatch(
    action: str,
    data: dict,
    *,
    agent_loop: AgentLoop,
    activity_log: ActivityLog,
    file_service: AgentFS,
    engine: ConfigEngine,
    ctx: WorkerContext | None = None,
) -> dict:
    """Route an action string to the typed handler. Raises ValueError for unknowns."""
    if action == "get_health":
        return handle_get_health(agent_loop)
    if action == "get_activity":
        return handle_get_activity(activity_log, GetActivityRequest(**data))
    if action == "get_mcp_tools":
        return handle_get_mcp_tools(agent_loop, data.get("server_key", ""))
    if action == "get_config":
        return handle_get_config(engine)
    # Config: split between plain domain (put_config) and full blob including secrets (put_secrets).
    if action == "put_config":
        return await handle_put_config(engine, PutConfigRequest(**data))
    if action == "put_secrets":
        if not ctx:
            return {"ok": False, "error": "Context required for put_secrets"}
        return await handle_apply_config(ctx, data.get("body", data))
    if action == "list_workspace":
        return handle_list_workspace(file_service, ListWorkspaceRequest(**data))
    if action == "read_file":
        return handle_read_file(file_service, ReadFileRequest(**data))
    if action == "write_file":
        return handle_write_file(file_service, WriteFileRequest(**data))
    if action == "delete_file":
        return handle_delete_file(file_service, DeleteFileRequest(**data))
    if action == "rename_file":
        return handle_rename_file(file_service, RenameFileRequest(**data))
    if action == "move_file":
        return handle_move_file(file_service, MoveFileRequest(**data))
    if action == "upload_file":
        return handle_upload_file(file_service, UploadFileRequest(**data))
    if action == "create_folder":
        return handle_create_folder(file_service, CreateFolderRequest(**data))
    if action == "install_skill":
        return await handle_install_skill(file_service, InstallSkillRequest(**data))
    if action == "uninstall_skill":
        return await handle_uninstall_skill(file_service, UninstallSkillRequest(**data))
    if action == "install_software":
        return await handle_install_software(
            agent_loop, InstallSoftwareRequest(**data), engine=engine
        )
    if action == "uninstall_software":
        return await handle_uninstall_software(
            agent_loop, UninstallSoftwareRequest(**data), engine=engine
        )
    raise ValueError(f"Unknown action: {action}")
