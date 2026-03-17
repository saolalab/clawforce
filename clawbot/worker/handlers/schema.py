"""Typed models for the worker ↔ admin WebSocket protocol.

Each request ``action`` has a typed payload (``*Request``) and a typed
result (``*Data``).  The ``dispatch`` function in ``admin.py`` maps
action strings to handlers that accept the request model and return
the response data.  Wire envelopes (register, heartbeat, request/response)
are plain dicts in AdminClient and ConnectionManager.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared payloads (used in handlers and/or wire serialization)
# ---------------------------------------------------------------------------


class ActivityEventPayload(BaseModel):
    agent_id: str = ""
    event_type: str = ""
    channel: str = ""
    content: str = ""
    timestamp: str = ""
    tool_name: str | None = None
    result_status: str | None = None
    duration_ms: int | None = None


# ---------------------------------------------------------------------------
# Per-action request / response payloads
# ---------------------------------------------------------------------------


class SoftwareWarning(BaseModel):
    key: str
    name: str
    command: str


class HealthData(BaseModel):
    status: str = "ok"
    mcp: dict[str, Any] | None = None
    software_warnings: list[SoftwareWarning] | None = None
    software_installing: bool = False


class GetActivityRequest(BaseModel):
    action: Literal["get_activity"] = "get_activity"
    limit: int = 50


class PutConfigRequest(BaseModel):
    action: Literal["put_config"] = "put_config"
    body: dict[str, Any] = Field(default_factory=dict)


class ListWorkspaceRequest(BaseModel):
    action: Literal["list_workspace"] = "list_workspace"
    root: Literal["workspace", "profiles"] = "workspace"


class FileListData(BaseModel):
    files: list[str] = Field(default_factory=list)


class ReadFileRequest(BaseModel):
    action: Literal["read_file"] = "read_file"
    path: str = ""


class FileContentData(BaseModel):
    content: str = ""


class WriteFileRequest(BaseModel):
    action: Literal["write_file"] = "write_file"
    path: str = ""
    content: str = ""


class DeleteFileRequest(BaseModel):
    action: Literal["delete_file"] = "delete_file"
    path: str = ""


class RenameFileRequest(BaseModel):
    action: Literal["rename_file"] = "rename_file"
    path: str = ""
    new_name: str = ""


class MoveFileRequest(BaseModel):
    action: Literal["move_file"] = "move_file"
    src_path: str = ""
    dest_path: str = ""


class UploadFileRequest(BaseModel):
    action: Literal["upload_file"] = "upload_file"
    path: str = ""
    content: str = ""  # base64-encoded binary content
    encoding: Literal["base64"] = "base64"


class CreateFolderRequest(BaseModel):
    action: Literal["create_folder"] = "create_folder"
    path: str = ""


class InstallSkillRequest(BaseModel):
    action: Literal["install_skill"] = "install_skill"
    slug: str = ""
    env: dict[str, str] = Field(default_factory=dict)


class SkillResultData(BaseModel):
    ok: bool = True
    slug: str = ""
    message: str = ""


class UninstallSkillRequest(BaseModel):
    action: Literal["uninstall_skill"] = "uninstall_skill"
    slug: str = ""


class InstallSoftwareRequest(BaseModel):
    action: Literal["install_software"] = "install_software"
    slug: str = ""
    package: str = ""
    install_type: str = "npm"
    name: str = ""
    description: str = ""
    skill_content: str = ""
    command: str = ""
    args: list[str] = Field(default_factory=list)
    stdin: bool = False
    env: dict[str, str] = Field(default_factory=dict)


class UninstallSoftwareRequest(BaseModel):
    action: Literal["uninstall_software"] = "uninstall_software"
    slug: str = ""


class SoftwareResultData(BaseModel):
    ok: bool = True
    slug: str = ""
    message: str = ""
    logs: str = ""
    exit_code: int = 0
    verified: bool = False
    resolved_command: str = ""
