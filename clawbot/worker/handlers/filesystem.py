"""Filesystem handlers for workspace file operations.

Handles list, read, write, upload, delete, rename, and move operations on workspace files.
"""

import base64

from clawbot.agent.agent_fs import AgentFS
from clawbot.worker.handlers.schema import (
    CreateFolderRequest,
    DeleteFileRequest,
    FileContentData,
    FileListData,
    ListWorkspaceRequest,
    MoveFileRequest,
    ReadFileRequest,
    RenameFileRequest,
    UploadFileRequest,
    WriteFileRequest,
)


def handle_list_workspace(file_service: AgentFS, req: ListWorkspaceRequest) -> dict:
    if req.root == "profiles":
        files = file_service.list_profile()
    else:
        files = file_service.list_workspace()
    return {"data": FileListData(files=files).model_dump()}


def handle_read_file(file_service: AgentFS, req: ReadFileRequest) -> dict:
    path = req.path.lstrip("/")
    if ".." in path:
        raise PermissionError("Invalid path")
    if path.startswith("profiles/"):
        rel = path[len("profiles/") :].lstrip("/")
        content = file_service.read_profile(rel)
    else:
        content = file_service.read_workspace(path)
    if content is None:
        raise FileNotFoundError(f"File not found: {path}")
    return {"data": FileContentData(content=content).model_dump()}


def handle_write_file(file_service: AgentFS, req: WriteFileRequest) -> dict:
    path = req.path.lstrip("/")
    if ".." in path:
        raise PermissionError("Invalid path")
    if path.startswith("profiles/"):
        rel = path[len("profiles/") :].lstrip("/")
        ok = file_service.write_profile(rel, req.content)
    else:
        ok = file_service.write_workspace(path, req.content)
    if not ok:
        raise PermissionError(f"Cannot write to: {path}")
    return {"data": {"ok": True}}


def handle_delete_file(file_service: AgentFS, req: DeleteFileRequest) -> dict:
    path = req.path.lstrip("/")
    if ".." in path:
        raise PermissionError("Invalid path")
    if path.startswith("profiles/"):
        raise PermissionError("Cannot delete files in profiles/")
    if path.startswith("workspace/"):
        path = path[len("workspace/") :].lstrip("/")
    if not path:
        raise PermissionError("Cannot delete workspace root")
    ok = file_service.delete_workspace(path)
    if not ok:
        raise FileNotFoundError(f"Cannot delete: {path}")
    return {"data": {"ok": True}}


def handle_rename_file(file_service: AgentFS, req: RenameFileRequest) -> dict:
    path = req.path.lstrip("/")
    if ".." in path:
        raise PermissionError("Invalid path")
    if path.startswith("profiles/"):
        raise PermissionError("Cannot rename files in profiles/")
    if path.startswith("workspace/"):
        path = path[len("workspace/") :].lstrip("/")
    if not path:
        raise PermissionError("Cannot rename workspace root")
    ok = file_service.rename_workspace(path, req.new_name)
    if not ok:
        raise PermissionError(f"Cannot rename: {path}")
    return {"data": {"ok": True}}


def handle_move_file(file_service: AgentFS, req: MoveFileRequest) -> dict:
    src_path = req.src_path.lstrip("/")
    dest_path = req.dest_path.lstrip("/")
    if ".." in src_path or ".." in dest_path:
        raise PermissionError("Invalid path")
    if src_path.startswith("profiles/") or dest_path.startswith("profiles/"):
        raise PermissionError("Cannot move files in profiles/")
    if src_path.startswith("workspace/"):
        src_path = src_path[len("workspace/") :].lstrip("/")
    if dest_path.startswith("workspace/"):
        dest_path = dest_path[len("workspace/") :].lstrip("/")
    if not src_path or not dest_path:
        raise PermissionError("Cannot move workspace root")
    ok = file_service.move_workspace(src_path, dest_path)
    if not ok:
        raise PermissionError(f"Cannot move: {src_path} to {dest_path}")
    return {"data": {"ok": True}}


def handle_upload_file(file_service: AgentFS, req: UploadFileRequest) -> dict:
    """Handle binary file upload (base64-encoded content)."""
    path = req.path.lstrip("/")
    if ".." in path:
        raise PermissionError("Invalid path")
    if path.startswith("profiles/"):
        raise PermissionError("Cannot upload files to profiles/")
    if path.startswith("workspace/"):
        path = path[len("workspace/") :].lstrip("/")
    if not path:
        raise PermissionError("Cannot upload to workspace root")
    try:
        content = base64.b64decode(req.content)
    except Exception as e:
        raise ValueError(f"Invalid base64 content: {e}") from e
    ok = file_service.upload_workspace(path, content)
    if not ok:
        raise PermissionError(f"Cannot upload to: {path}")
    return {"data": {"ok": True, "size": len(content)}}


def handle_create_folder(file_service: AgentFS, req: CreateFolderRequest) -> dict:
    """Handle folder creation."""
    path = req.path.lstrip("/")
    if ".." in path:
        raise PermissionError("Invalid path")
    if path.startswith("profiles/"):
        raise PermissionError("Cannot create folders in profiles/")
    if path.startswith("workspace/"):
        path = path[len("workspace/") :].lstrip("/")
    if not path:
        raise PermissionError("Cannot create workspace root")
    ok = file_service.create_folder_workspace(path)
    if not ok:
        raise PermissionError(f"Cannot create folder: {path}")
    return {"data": {"ok": True}}
