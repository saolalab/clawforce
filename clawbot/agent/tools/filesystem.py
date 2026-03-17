"""File system tools: read, write, edit, list. Use AgentFS for workspace (r/w) and profiles (r/o)."""

from typing import Any

from clawbot.agent.agent_fs import AgentFS
from clawbot.agent.tools.base import Tool


class ReadFileTool(Tool):
    """Read a file. Accessible: workspace/ (read/write) and profiles/ (read-only)."""

    def __init__(self, file_service: AgentFS) -> None:
        self._fs = file_service

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file. Paths in workspace/ (read/write) or profiles/ (read-only). Use .agents/memory/MEMORY.md or .agents/skills/<name>/SKILL.md."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path (e.g. .agents/memory/MEMORY.md or .agents/skills/github/SKILL.md)",
                }
            },
            "required": ["path"],
        }

    async def execute(self, path: str, **kwargs: Any) -> str:
        try:
            file_path = self._fs.resolve_read(path)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            if not file_path.is_file():
                return f"Error: Not a file: {path}"
            return file_path.read_text(encoding="utf-8")
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error reading file: {str(e)}"


class WriteFileTool(Tool):
    """Write to a file in workspace/. profiles/ is read-only and cannot be written to."""

    def __init__(self, file_service: AgentFS) -> None:
        self._fs = file_service

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file in workspace/. Cannot write to profiles/ (read-only)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path under workspace/"},
                "content": {"type": "string", "description": "The content to write"},
            },
            "required": ["path", "content"],
        }

    async def execute(self, path: str, content: str, **kwargs: Any) -> str:
        try:
            file_path = self._fs.resolve_write(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} bytes to {path}"
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error writing file: {str(e)}"


class EditFileTool(Tool):
    """Edit a file by replacing text. Only files in workspace/ can be edited."""

    def __init__(self, file_service: AgentFS) -> None:
        self._fs = file_service

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Edit a file by replacing old_text with new_text. Only workspace/ files can be edited; profiles/ is read-only."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to edit (under workspace/)",
                },
                "old_text": {"type": "string", "description": "The exact text to find and replace"},
                "new_text": {"type": "string", "description": "The text to replace with"},
            },
            "required": ["path", "old_text", "new_text"],
        }

    async def execute(self, path: str, old_text: str, new_text: str, **kwargs: Any) -> str:
        try:
            file_path = self._fs.resolve_write(path)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            content = file_path.read_text(encoding="utf-8")
            if old_text not in content:
                return "Error: old_text not found in file. Make sure it matches exactly."
            count = content.count(old_text)
            if count > 1:
                return f"Warning: old_text appears {count} times. Please provide more context to make it unique."
            new_content = content.replace(old_text, new_text, 1)
            file_path.write_text(new_content, encoding="utf-8")
            return f"Successfully edited {path}"
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error editing file: {str(e)}"


class ListDirTool(Tool):
    """List directory contents in workspace/ or profiles/."""

    def __init__(self, file_service: AgentFS) -> None:
        self._fs = file_service

    @property
    def name(self) -> str:
        return "list_dir"

    @property
    def description(self) -> str:
        return "List directory contents (one level). Use path '.' or 'workspace' or 'profiles' or a path under them. For full workspace overview, use workspace_tree instead."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path (e.g. . or workspace or .agents/memory or .agents/skills)",
                }
            },
            "required": ["path"],
        }

    async def execute(self, path: str, **kwargs: Any) -> str:
        try:
            items = self._fs.list_dir(path or ".")
            if not items:
                return f"Directory {path or '.'} is empty"
            return "\n".join(items)
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error listing directory: {str(e)}"


class WorkspaceTreeTool(Tool):
    """Get a hierarchical tree view of workspace or profiles. Use for overview instead of dumping list_dir."""

    def __init__(self, file_service: AgentFS) -> None:
        self._fs = file_service

    @property
    def name(self) -> str:
        return "workspace_tree"

    @property
    def description(self) -> str:
        return "Get a hierarchical tree of workspace or profiles. Prefer this over repeated list_dir when exploring structure. Organize new files into folders (docs/, projects/, outputs/) per WORKSPACE_LAYOUT.md."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "root": {
                    "type": "string",
                    "description": "Root to show: 'workspace' (default) or 'profiles'",
                    "enum": ["workspace", "profiles"],
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Max tree depth (default 6). Deeper paths are collapsed.",
                },
            },
            "required": [],
        }

    async def execute(
        self,
        root: str = "workspace",
        max_depth: int = 6,
        **kwargs: Any,
    ) -> str:
        try:
            return self._fs.list_dir_tree(root=root, max_depth=max_depth)
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error building tree: {str(e)}"
