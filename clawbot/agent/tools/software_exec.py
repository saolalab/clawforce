"""Software exec tool: run an installed software (catalog) by key via SoftwareManagement."""

import logging
from pathlib import Path
from typing import Any

from clawbot.agent.tools.base import Tool
from clawbot.core.software import SOFTWARE_EXEC_MAX_OUTPUT_CHARS, SoftwareManagement

logger = logging.getLogger(__name__)


class SoftwareExecTool(Tool):
    """
    Run an installed software from the catalog by key (e.g. claude_code).
    Uses SoftwareManagement.execute (PTY). Catalog is live (hot reload).
    """

    def __init__(
        self,
        software_management: SoftwareManagement,
        workspace: Path | str,
        max_output_chars: int = SOFTWARE_EXEC_MAX_OUTPUT_CHARS,
    ):
        self._software_management = software_management
        self._workspace = Path(workspace) if isinstance(workspace, str) else workspace
        self._max_output_chars = max_output_chars

    @property
    def name(self) -> str:
        return "software_exec"

    @property
    def description(self) -> str:
        keys = self._software_management.list_keys()
        if keys:
            return (
                "Run an installed software by key. Send the backend_key and a task; "
                f"returns the CLI output. Available keys: {', '.join(keys)}. "
                "Catalog is live (new installs appear without restart)."
            )
        return (
            "Run an installed software by key. No software installed yet; "
            "install from the software catalog and use backend_key. Catalog is live (hot reload)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        keys = self._software_management.list_keys()
        backend_key_schema: dict[str, Any] = {
            "type": "string",
            "description": "Installed software key (e.g. from catalog). "
            + (f"Available: {', '.join(keys)}." if keys else "Install software first."),
        }
        if keys:
            backend_key_schema["enum"] = keys
        return {
            "type": "object",
            "properties": {
                "backend_key": backend_key_schema,
                "task": {
                    "type": "string",
                    "description": "The task or prompt to send to the software",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory path; defaults to the agent workspace",
                },
            },
            "required": ["backend_key", "task"],
        }

    async def execute(
        self,
        backend_key: str,
        task: str,
        working_dir: str | None = None,
        **kwargs: Any,
    ) -> str:
        return await self._software_management.execute(
            key=backend_key,
            task=task,
            working_dir=working_dir,
            workspace=self._workspace,
            max_output_chars=self._max_output_chars,
        )
