"""Agent filesystem: list/read/write files via the runtime (WebSocket to worker).

Two roots:
- workspace/ — agent r/w sandbox
- profiles/  — agent r/o (character setup: AGENTS, TOOLS, skills)

Both roots are fully writable from the admin side.  The ``agent_read_only``
flag in the list response tells the UI which root the *agent* cannot modify.
All operations require the agent to be online (no storage fallback).
"""

import io
import logging
import zipfile

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from clawforce.auth import get_current_user
from clawforce.core.authz import require_agent_access
from clawforce.core.domain.runtime import AgentRuntimeBackend, AgentRuntimeError
from clawforce.core.path_utils import validate_path_for_api
from clawforce.core.store.agents import AgentStore
from clawforce.deps import get_agent_store, get_runtime

router = APIRouter(tags=["workspace"])

ROOT_WORKSPACE = "workspace"
ROOT_PROFILES = "profiles"


@router.get("/api/agents/{agent_id}/workspace")
async def list_files(
    request: Request,
    agent_id: str,
    root: str = Query(ROOT_WORKSPACE, description="Root: workspace (r/w) or profiles (r/o)"),
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, agent)
    try:
        if root == ROOT_PROFILES:
            files = await runtime.list_profile(agent_id)
            return {"files": files, "agent_read_only": True, "root": ROOT_PROFILES}
        files = await runtime.list_workspace(agent_id)
        return {"files": files, "agent_read_only": False, "root": ROOT_WORKSPACE}
    except AgentRuntimeError as exc:
        detail = str(exc)
        manager = getattr(request.app.state, "ws_manager", None)
        connected = list(manager._connections.keys()) if manager else []
        logging.getLogger(__name__).warning(
            "Workspace 503 for agent %s (not connected). Connected agents: %s",
            agent_id,
            connected,
        )
        if "not connected" in detail.lower():
            detail += (
                " In Docker mode, set ADMIN_PUBLIC_URL to a URL reachable from the agent container "
                "(e.g. http://host.docker.internal:8080 on Mac/Windows)."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )


@router.get("/api/agents/{agent_id}/workspace/{path:path}")
async def read_file(
    agent_id: str,
    path: str,
    download: bool = Query(False, description="Return as downloadable attachment"),
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, agent)
    path = validate_path_for_api(path)
    try:
        is_profiles = path.startswith("profiles/")
        is_workspace = path.startswith("workspace/")
        if is_profiles:
            rel = path[len("profiles/") :].lstrip("/")
            content = await runtime.read_profile_file(agent_id, rel)
        else:
            rel = path[len("workspace/") :].lstrip("/") if is_workspace else path
            content = await runtime.read_workspace_file(agent_id, rel)
    except AgentRuntimeError as exc:
        detail = str(exc)
        if "not connected" in detail.lower():
            detail += (
                " In Docker mode, set ADMIN_PUBLIC_URL to a URL reachable from the agent container "
                "(e.g. http://host.docker.internal:8080 on Mac/Windows)."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if download:
        filename = path.rsplit("/", 1)[-1]
        return Response(
            content=content.encode("utf-8"),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return PlainTextResponse(content)


class WriteBody(BaseModel):
    content: str = ""


class RenameBody(BaseModel):
    new_name: str = ""


class MoveBody(BaseModel):
    dest_path: str = ""


@router.put("/api/agents/{agent_id}/workspace/{path:path}")
async def write_file(
    agent_id: str,
    path: str,
    body: WriteBody = Body(...),
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, agent)
    path = validate_path_for_api(path)
    try:
        is_profiles = path.startswith("profiles/")
        is_workspace = path.startswith("workspace/")
        if is_profiles:
            rel = path[len("profiles/") :].lstrip("/")
            ok = await runtime.write_profile_file(agent_id, rel, body.content)
        else:
            rel = path[len("workspace/") :].lstrip("/") if is_workspace else path
            ok = await runtime.write_workspace_file(agent_id, rel, body.content)
    except AgentRuntimeError as exc:
        detail = str(exc)
        if "not connected" in detail.lower():
            detail += (
                " In Docker mode, set ADMIN_PUBLIC_URL to a URL reachable from the agent container "
                "(e.g. http://host.docker.internal:8080 on Mac/Windows)."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File write failed"
        )
    return {"ok": True}


@router.delete("/api/agents/{agent_id}/workspace/{path:path}")
async def delete_file(
    agent_id: str,
    path: str,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Delete a file or directory in the workspace."""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, agent)
    path = validate_path_for_api(path)
    if path.startswith("profiles/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete files in profiles/"
        )
    try:
        is_workspace = path.startswith("workspace/")
        rel = path[len("workspace/") :].lstrip("/") if is_workspace else path
        ok = await runtime.delete_workspace_file(agent_id, rel)
    except AgentRuntimeError as exc:
        detail = str(exc)
        if "not connected" in detail.lower():
            detail += (
                " In Docker mode, set ADMIN_PUBLIC_URL to a URL reachable from the agent container "
                "(e.g. http://host.docker.internal:8080 on Mac/Windows)."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File or directory not found"
        )
    return {"ok": True}


@router.post("/api/agents/{agent_id}/workspace/{path:path}/rename")
async def rename_file(
    agent_id: str,
    path: str,
    body: RenameBody = Body(...),
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Rename a file or directory in the workspace."""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, agent)
    path = validate_path_for_api(path)
    if path.startswith("profiles/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot rename files in profiles/"
        )
    if not body.new_name or "/" in body.new_name or ".." in body.new_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid new name")
    try:
        is_workspace = path.startswith("workspace/")
        rel = path[len("workspace/") :].lstrip("/") if is_workspace else path
        ok = await runtime.rename_workspace_file(agent_id, rel, body.new_name)
    except AgentRuntimeError as exc:
        detail = str(exc)
        if "not connected" in detail.lower():
            detail += (
                " In Docker mode, set ADMIN_PUBLIC_URL to a URL reachable from the agent container "
                "(e.g. http://host.docker.internal:8080 on Mac/Windows)."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rename failed (file not found or destination exists)",
        )
    return {"ok": True}


@router.post("/api/agents/{agent_id}/workspace/{path:path}/move")
async def move_file(
    agent_id: str,
    path: str,
    body: MoveBody = Body(...),
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Move a file or directory in the workspace."""
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, agent)
    path = validate_path_for_api(path)
    dest_path = validate_path_for_api(body.dest_path)
    if path.startswith("profiles/") or dest_path.startswith("profiles/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot move files to/from profiles/"
        )
    try:
        is_workspace = path.startswith("workspace/")
        src_rel = path[len("workspace/") :].lstrip("/") if is_workspace else path
        is_workspace_dest = dest_path.startswith("workspace/")
        dest_rel = dest_path[len("workspace/") :].lstrip("/") if is_workspace_dest else dest_path
        ok = await runtime.move_workspace_file(agent_id, src_rel, dest_rel)
    except AgentRuntimeError as exc:
        detail = str(exc)
        if "not connected" in detail.lower():
            detail += (
                " In Docker mode, set ADMIN_PUBLIC_URL to a URL reachable from the agent container "
                "(e.g. http://host.docker.internal:8080 on Mac/Windows)."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Move failed (file not found or destination exists)",
        )
    return {"ok": True}


@router.get("/api/agents/{agent_id}/workspace-download/{folder:path}")
async def download_folder_zip(
    agent_id: str,
    folder: str,
    current: dict = Depends(get_current_user),
    store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Download a folder as a zip archive.

    ``folder`` is a tree path like ``workspace/src`` or ``profiles/config``.
    The first segment determines the root (workspace vs profiles).
    """
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_agent_access(current, agent)
    folder = validate_path_for_api(folder)

    is_profiles = folder == ROOT_PROFILES or folder.startswith(f"{ROOT_PROFILES}/")
    if is_profiles:
        prefix = folder[len(f"{ROOT_PROFILES}/") :] if "/" in folder else ""
        try:
            all_files = await runtime.list_profile(agent_id)
        except AgentRuntimeError as exc:
            detail = str(exc)
            if "not connected" in detail.lower():
                detail += (
                    " In Docker mode, set ADMIN_PUBLIC_URL to a URL reachable from the agent container "
                    "(e.g. http://host.docker.internal:8080 on Mac/Windows)."
                )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            )
        read_fn = runtime.read_profile_file
    else:
        prefix = folder[len(f"{ROOT_WORKSPACE}/") :] if "/" in folder else ""
        try:
            all_files = await runtime.list_workspace(agent_id)
        except AgentRuntimeError as exc:
            detail = str(exc)
            if "not connected" in detail.lower():
                detail += (
                    " In Docker mode, set ADMIN_PUBLIC_URL to a URL reachable from the agent container "
                    "(e.g. http://host.docker.internal:8080 on Mac/Windows)."
                )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            )
        read_fn = runtime.read_workspace_file

    matched = [f for f in all_files if not prefix or f == prefix or f.startswith(f"{prefix}/")]
    if not matched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No files in folder")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in matched:
            try:
                content = await read_fn(agent_id, fpath)
                if content is not None:
                    arc_name = fpath[len(f"{prefix}/") :] if prefix else fpath
                    zf.writestr(arc_name, content.encode("utf-8"))
            except AgentRuntimeError:
                continue

    folder_name = folder.rsplit("/", 1)[-1] or folder
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{folder_name}.zip"'},
    )
