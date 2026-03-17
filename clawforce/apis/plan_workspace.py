"""Plan workspace filesystem API.

Provides file management for plans similar to agent workspace:
- List files
- Read/write files
- Delete files/directories
- Rename files/directories
- Move files/directories
- Create folders
- Upload files
- Download files/folders as ZIP

Access control:
- Admin users have full access to all plan workspaces
- Agents assigned to a plan have full read/write access to that plan's workspace
"""

import io
import zipfile

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from clawforce.auth import get_user_or_agent
from clawforce.core.path_utils import validate_path_for_api
from clawforce.core.plan_access import require_plan_access
from clawforce.core.store.plan_workspace import PlanWorkspaceStore
from clawforce.core.store.plans import PlanStore
from clawforce.deps import get_plan_store

router = APIRouter(tags=["plan-workspace"])


def _get_plan_workspace_store() -> PlanWorkspaceStore:
    return PlanWorkspaceStore()


class WriteBody(BaseModel):
    content: str = ""


class RenameBody(BaseModel):
    new_name: str = ""


class MoveBody(BaseModel):
    dest_path: str = ""


@router.get("/api/plans/{plan_id}/workspace")
def list_workspace_files(
    plan_id: str,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    workspace: PlanWorkspaceStore = Depends(_get_plan_workspace_store),
):
    """List all files in the plan workspace."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    files = workspace.list_files(plan_id)
    return {"files": files, "root": "workspace"}


@router.get("/api/plans/{plan_id}/workspace/{path:path}")
def read_workspace_file(
    plan_id: str,
    path: str,
    download: bool = Query(False, description="Return as downloadable attachment"),
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    workspace: PlanWorkspaceStore = Depends(_get_plan_workspace_store),
):
    """Read a file from the plan workspace."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    path = validate_path_for_api(path)

    if download:
        data = workspace.read_file_binary(plan_id, path)
        if data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        filename = path.rsplit("/", 1)[-1]
        return Response(
            content=data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    content = workspace.read_file(plan_id, path)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return PlainTextResponse(content)


@router.put("/api/plans/{plan_id}/workspace/{path:path}")
def write_workspace_file(
    plan_id: str,
    path: str,
    body: WriteBody = Body(...),
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    workspace: PlanWorkspaceStore = Depends(_get_plan_workspace_store),
):
    """Write a text file to the plan workspace."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    path = validate_path_for_api(path)
    if not workspace.write_file(plan_id, path, body.content):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to write file"
        )
    return {"ok": True}


@router.post("/api/plans/{plan_id}/workspace/upload")
async def upload_workspace_file(
    plan_id: str,
    file: UploadFile,
    path: str = Query("", description="Optional subdirectory path"),
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    workspace: PlanWorkspaceStore = Depends(_get_plan_workspace_store),
):
    """Upload a file to the plan workspace."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)

    data = await file.read()
    filename = file.filename or "uploaded_file"

    if path:
        path = validate_path_for_api(path)
        full_path = f"{path}/{filename}"
    else:
        full_path = filename

    if not workspace.write_file_binary(plan_id, full_path, data):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload file"
        )
    return {"ok": True, "path": full_path}


@router.delete("/api/plans/{plan_id}/workspace/{path:path}")
def delete_workspace_file(
    plan_id: str,
    path: str,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    workspace: PlanWorkspaceStore = Depends(_get_plan_workspace_store),
):
    """Delete a file or directory from the plan workspace."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    path = validate_path_for_api(path)
    if not workspace.delete_file(plan_id, path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File or directory not found"
        )
    return {"ok": True}


@router.post("/api/plans/{plan_id}/workspace/{path:path}/rename")
def rename_workspace_file(
    plan_id: str,
    path: str,
    body: RenameBody = Body(...),
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    workspace: PlanWorkspaceStore = Depends(_get_plan_workspace_store),
):
    """Rename a file or directory in the plan workspace."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    path = validate_path_for_api(path)
    if not body.new_name or "/" in body.new_name or ".." in body.new_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid new name")
    if not workspace.rename_file(plan_id, path, body.new_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rename failed (file not found or destination exists)",
        )
    return {"ok": True}


@router.post("/api/plans/{plan_id}/workspace/{path:path}/move")
def move_workspace_file(
    plan_id: str,
    path: str,
    body: MoveBody = Body(...),
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    workspace: PlanWorkspaceStore = Depends(_get_plan_workspace_store),
):
    """Move a file or directory within the plan workspace."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    path = validate_path_for_api(path)
    dest_path = validate_path_for_api(body.dest_path)
    if not workspace.move_file(plan_id, path, dest_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Move failed (file not found or destination exists)",
        )
    return {"ok": True}


@router.post("/api/plans/{plan_id}/workspace-folder/{path:path}")
def create_workspace_folder(
    plan_id: str,
    path: str,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    workspace: PlanWorkspaceStore = Depends(_get_plan_workspace_store),
):
    """Create a folder in the plan workspace."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    path = validate_path_for_api(path)
    if not workspace.create_folder(plan_id, path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create folder"
        )
    return {"ok": True}


@router.get("/api/plans/{plan_id}/workspace-download/{folder:path}")
def download_workspace_folder(
    plan_id: str,
    folder: str,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    workspace: PlanWorkspaceStore = Depends(_get_plan_workspace_store),
):
    """Download a folder as a ZIP archive."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    folder = validate_path_for_api(folder) if folder else ""

    all_files = workspace.list_files(plan_id)
    if folder:
        matched = [f for f in all_files if f == folder or f.startswith(f"{folder}/")]
    else:
        matched = all_files

    if not matched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No files in folder")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in matched:
            content = workspace.read_file_binary(plan_id, fpath)
            if content is not None:
                arc_name = fpath[len(f"{folder}/") :] if folder else fpath
                zf.writestr(arc_name, content)

    folder_name = folder.rsplit("/", 1)[-1] if folder else "workspace"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{folder_name}.zip"'},
    )
