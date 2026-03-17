"""Shell execution tool — workspace-restricted command runner."""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any

from clawbot.agent.tools.base import Tool
from clawbot.agent.tools.policy import ShellCommandPolicy

logger = logging.getLogger(__name__)

# Absolute-path patterns (POSIX and Windows) — used for workspace restriction checks
_POSIX_ABS = re.compile(r"(?:^|[\s;|>&(])(/[^\s\"'>)]*)")
_WIN_ABS = re.compile(r"[A-Za-z]:\\[^\\\"']+")


class ExecTool(Tool):
    """Tool to execute shell commands inside the workspace."""

    def __init__(
        self,
        timeout: int = 60,
        working_dir: str | None = None,
        deny_patterns: list[str] | None = None,
        allow_patterns: list[str] | None = None,
        restrict_to_workspace: bool = True,
        policy: ShellCommandPolicy | None = None,
    ):
        self.timeout = timeout
        self.working_dir = working_dir
        self.policy = policy or ShellCommandPolicy()
        self.deny_patterns = deny_patterns or [
            r"\brm\s+-[rf]{1,2}\b",
            r"\bdel\s+/[fq]\b",
            r"\brmdir\s+/s\b",
            r"\b(format|mkfs|diskpart)\b",
            r"\bdd\s+if=",
            r">\s*/dev/sd",
            r"\b(shutdown|reboot|poweroff)\b",
            r":\(\)\s*\{.*\};\s*:",
            # Block env/printenv to prevent leaking secrets from environment
            r"^\s*(env|printenv)\s*$",
            r"\benv\s*\|",  # env | grep, etc.
            r"\bprintenv\b",
        ]
        self.allow_patterns = allow_patterns or []
        self.restrict_to_workspace = restrict_to_workspace

    @property
    def name(self) -> str:
        return "exec"

    @property
    def description(self) -> str:
        desc = "Execute a shell command and return its output."
        if self.restrict_to_workspace:
            desc += " Commands are restricted to the workspace directory."
        return desc

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
            },
            "required": ["command"],
        }

    async def execute(self, command: str, **kwargs: Any) -> str:
        cwd = self.working_dir or os.getcwd()

        guard_error = self._guard_command(command)
        if guard_error:
            return guard_error

        env = os.environ.copy()
        if self.restrict_to_workspace and self.working_dir:
            env["HOME"] = self.working_dir
            env["TMPDIR"] = self.working_dir

        # Ensure ~/.local/bin (real home) is in PATH so software installed there
        # (e.g. gh, pip --user) is found even when HOME is overridden to workspace.
        local_bin = Path.home() / ".local" / "bin"
        if local_bin.is_dir():
            current_path = env.get("PATH", "")
            local_bin_str = str(local_bin)
            if local_bin_str not in current_path:
                env["PATH"] = f"{local_bin_str}:{current_path}"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return f"Error: Command timed out after {self.timeout} seconds"

            output_parts = []

            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))

            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():
                    output_parts.append(f"STDERR:\n{stderr_text}")

            if process.returncode != 0:
                output_parts.append(f"\nExit code: {process.returncode}")

            result = "\n".join(output_parts) if output_parts else "(no output)"

            max_len = 10000
            if len(result) > max_len:
                result = result[:max_len] + f"\n... (truncated, {len(result) - max_len} more chars)"

            return result

        except Exception as e:
            return f"Error executing command: {str(e)}"

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    # Patterns for commands that access paths outside workspace
    _PATH_COMMANDS = re.compile(
        r"\b(ls|cat|head|tail|less|more|file|stat|find|grep|wc|du|df|tree|"
        r"cp|mv|rm|touch|mkdir|chmod|chown|ln|readlink|realpath)\b"
    )

    def _guard_command(self, command: str) -> str | None:
        """Reject commands that escape the workspace or are destructive."""
        cmd = command.strip()
        ok, reason = self.policy.check(command)
        if not ok:
            return f"Error: {reason}"

        lower = cmd.lower()
        for pattern in self.deny_patterns:
            if re.search(pattern, lower):
                return "Error: Command blocked by safety guard (dangerous pattern detected)"

        if self.allow_patterns:
            if not any(re.search(p, lower) for p in self.allow_patterns):
                return "Error: Command blocked by safety guard (not in allowlist)"

        if not self.restrict_to_workspace:
            return None

        # --- workspace restriction checks ---

        if "..\\" in cmd or "../" in cmd:
            return "Error: Command blocked — path traversal not allowed"

        # Block access to hidden config directories and sensitive files (contains secrets)
        if re.search(r"\.config\b|\.sessions\b|\.logs\b|agent\.json\b", cmd):
            return "Error: Command blocked — cannot access config directories or agent.json"

        ws_root = Path(self.working_dir).resolve() if self.working_dir else None
        if ws_root is None:
            logger.warning(
                "restrict_to_workspace=True but working_dir is not set — blocking command"
            )
            return "Error: Command blocked — workspace directory not configured"

        # Block every absolute path that is not inside the workspace.
        for raw in _WIN_ABS.findall(cmd) + _POSIX_ABS.findall(cmd):
            try:
                p = Path(raw.strip()).resolve()
            except Exception:
                continue
            if not p.is_relative_to(ws_root):
                return f"Error: Command blocked — path '{raw.strip()}' is outside the workspace"

        # Block path commands with just "/" or system paths
        if self._PATH_COMMANDS.search(cmd):
            # Check for bare "/" as argument (ls /, cat /etc/passwd, etc.)
            if re.search(r"\s+/\s*$|\s+/\s+", cmd) or cmd.endswith(" /"):
                return "Error: Command blocked — cannot access root filesystem"
            # Check for system directories and /data (contains other agents' data)
            if re.search(r"\s+/(etc|var|usr|s?bin|home|root|proc|sys|dev|tmp|data)\b", cmd):
                return "Error: Command blocked — cannot access system directories"
            # Also block /agent (when using isolated mount) parent traversal
            if re.search(r"\s+/agent\s*$|\s+/agent/\.\.", cmd):
                return "Error: Command blocked — cannot access parent of agent directory"

        # Block cd to an absolute path outside workspace
        cd_match = re.search(r"\bcd\s+([^\s;|&]+)", cmd)
        if cd_match:
            target = cd_match.group(1)
            if target.startswith("/") or (len(target) >= 2 and target[1] == ":"):
                try:
                    p = Path(target).resolve()
                except Exception:
                    pass
                else:
                    if not p.is_relative_to(ws_root):
                        return f"Error: Command blocked — cd target '{target}' is outside the workspace"

        return None
