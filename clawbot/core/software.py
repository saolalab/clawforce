"""Software management: install, uninstall, config, reload, execute, register.

Single place for catalog (in-memory + optional file persistence), running
installed CLIs via PTY, and install/uninstall/reinstall. Used by the agent loop,
subagent software_exec tool, worker handlers, and lifespan reinstall.
"""

import asyncio
import fcntl
import json
import logging
import os
import pty
import re
import shutil
import struct
import termios
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawbot.core.config.loader import load_config, save_config
from clawlib.config.loader import _load_raw

logger = logging.getLogger(__name__)

SOFTWARE_EXEC_MAX_OUTPUT_CHARS = 128_000

_NPM_GLOBAL_BIN: str | None = None

_ANSI_RE = re.compile(
    r"\x1b\[[0-9;?]*[A-Za-z]"
    r"|\x1b\][^\x07]*\x07"
    r"|\x1b[()][A-B012]"
    r"|\x1b[=>NOMDEHc78]"
    r"|\r"
)


def slug_to_key(slug: str) -> str:
    """Normalize slug to catalog key (safe for tool names and config)."""
    key = slug.replace("/", "_").replace(".", "_").replace("@", "_").strip("_")
    return key or "software"


def _entry_to_dict(entry: Any) -> dict[str, Any]:
    if hasattr(entry, "model_dump"):
        return entry.model_dump()
    if isinstance(entry, dict):
        return dict(entry)
    return {}


def _get_entry_attr(entry: dict[str, Any], attr: str, default: Any = "") -> Any:
    if attr in entry:
        return entry[attr]
    camel = "".join(p.capitalize() if i else p for i, p in enumerate(attr.split("_")))
    return entry.get(camel, entry.get(attr, default))


async def _get_npm_global_bin() -> str:
    global _NPM_GLOBAL_BIN  # noqa: PLW0603
    if _NPM_GLOBAL_BIN is not None:
        return _NPM_GLOBAL_BIN
    try:
        proc = await asyncio.create_subprocess_exec(
            "npm",
            "config",
            "get",
            "prefix",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        prefix = out.decode("utf-8").strip()
        _NPM_GLOBAL_BIN = str(Path(prefix) / "bin") if prefix else ""
    except Exception:
        _NPM_GLOBAL_BIN = ""
    return _NPM_GLOBAL_BIN


async def _find_binary(
    command: str,
    install_type: str = "",
    env: dict[str, str] | None = None,
) -> str:
    """Return the absolute path to `command`, or the bare name if not found.

    Search order:
      1. Already absolute → return as-is.
      2. shutil.which (respects current PATH).
      3. npm global bin (npm config get prefix)/bin  — for npm packages.
      4. ~/.local/bin                                — for pip/shell packages.

    When `env` is provided and the binary is found outside the current PATH,
    its directory is prepended to env["PATH"] so child processes find it too.
    """
    if not command or os.path.isabs(command):
        return command
    found = shutil.which(command)
    if found:
        return found
    if install_type in ("npm", ""):
        npm_bin = await _get_npm_global_bin()
        if npm_bin:
            candidate = Path(npm_bin) / command
            if candidate.is_file():
                if env is not None and npm_bin not in env.get("PATH", ""):
                    env["PATH"] = f"{npm_bin}:{env.get('PATH', '')}"
                return str(candidate)
    if install_type in ("pip", "shell", ""):
        candidate = Path.home() / ".local" / "bin" / command
        if candidate.is_file():
            if env is not None:
                bin_dir = str(candidate.parent)
                if bin_dir not in env.get("PATH", ""):
                    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            return str(candidate)
    return command


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


async def _run_with_pty(
    cmd: list[str],
    cwd: str,
    env: dict[str, str],
    stdin_data: bytes | None,
    timeout: int = 0,
) -> str:
    master_fd, slave_fd = pty.openpty()
    winsize = struct.pack("HHHH", 50, 160, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            env=env,
        )
    except Exception:
        os.close(slave_fd)
        os.close(master_fd)
        raise

    os.close(slave_fd)

    if stdin_data:
        try:
            os.write(master_fd, stdin_data)
            os.write(master_fd, b"\x04")
        except OSError:
            pass

    os.set_blocking(master_fd, False)
    output = bytearray()
    loop = asyncio.get_running_loop()
    readable = asyncio.Event()

    def _on_readable() -> None:
        readable.set()

    loop.add_reader(master_fd, _on_readable)

    async def _drain() -> None:
        while True:
            await readable.wait()
            readable.clear()
            try:
                while True:
                    chunk = os.read(master_fd, 65_536)
                    if not chunk:
                        return
                    output.extend(chunk)
            except BlockingIOError:
                continue
            except OSError:
                return

    drain_task = asyncio.create_task(_drain())
    timed_out = False
    try:
        if timeout > 0:
            await asyncio.wait_for(proc.wait(), timeout=float(timeout))
        else:
            await proc.wait()
    except asyncio.TimeoutError:
        timed_out = True
        proc.kill()
        await proc.wait()

    try:
        await asyncio.wait_for(drain_task, timeout=3.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        drain_task.cancel()

    try:
        loop.remove_reader(master_fd)
    except Exception:
        pass
    os.close(master_fd)

    if timed_out:
        return f"Error: software did not complete within {timeout}s (timeout)."
    return _strip_ansi(output.decode("utf-8", errors="replace")).strip()


async def _run_post_install(
    post_install: dict[str, Any],
    install_type: str,
    extra_env: dict[str, str] | None = None,
) -> None:
    """Run post_install hook after software install. Supports daemon mode for long-running processes.

    post_install: { "command": str, "args"?: list, "daemon"?: bool, "env"?: dict }
    If daemon is True, spawns process in background without waiting.
    extra_env and post_install.env are merged into the process environment (e.g. for credentials).
    """
    cmd_str = post_install.get("command") or ""
    if not cmd_str:
        return
    args_list = post_install.get("args") or []
    daemon = bool(post_install.get("daemon", False))
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    if isinstance(post_install.get("env"), dict):
        env.update(post_install["env"])
    resolved = await _find_binary(cmd_str, install_type, env=env)
    full_cmd = [resolved] + [str(a) for a in args_list]
    if daemon:
        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
        logger.info(f"Started post-install daemon: {' '.join(full_cmd)} (pid={proc.pid})")
    else:
        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        await asyncio.wait_for(proc.communicate(), timeout=60.0)
        if proc.returncode != 0:
            raise RuntimeError(f"post_install exited with code {proc.returncode}")


def _build_install_cmd(install_type: str, package: str) -> list[str]:
    """Return the shell command to install `package`, or [] for unknown install_type."""
    if install_type == "npm":
        return ["npm", "install", "-g", package, "--loglevel=error"]
    if install_type == "pip":
        return ["pip", "install", "--user", package]
    if install_type == "shell":
        return ["sh", "-c", package]
    return []


async def _run_install_with_retry(
    cmd: list[str],
    key: str,
    max_attempts: int = 3,
    base_delay: float = 5.0,
) -> bool:
    """Run a package-manager install command, retrying on transient failures.

    Streams output line-by-line at INFO level. Returns True on success.
    """
    for attempt in range(1, max_attempts + 1):
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            if proc.stdout:
                async for line_bytes in proc.stdout:
                    line = line_bytes.decode("utf-8", errors="replace").rstrip()
                    if line:
                        logger.info("[%s] %s", key, line)
            await asyncio.wait_for(proc.wait(), timeout=120.0)
        except asyncio.TimeoutError:
            if proc and proc.returncode is None:
                proc.kill()
            logger.warning(
                "Timed out reinstalling '%s' (attempt %d/%d)", key, attempt, max_attempts
            )
        except Exception as e:
            logger.warning(
                "Error reinstalling '%s' (attempt %d/%d): %s", key, attempt, max_attempts, e
            )
        else:
            if proc and proc.returncode == 0:
                return True
            logger.warning(
                "Reinstall of '%s' exited %s (attempt %d/%d)",
                key,
                proc.returncode if proc else "?",
                attempt,
                max_attempts,
            )

        if attempt < max_attempts:
            delay = base_delay * (2 ** (attempt - 1))
            logger.info("Retrying '%s' in %.1fs...", key, delay)
            await asyncio.sleep(delay)

    logger.error("Reinstall of '%s' failed after %d attempts", key, max_attempts)
    return False


class SoftwareManagement:
    """
    Central handling for software: catalog (in-memory + optional file), install,
    uninstall, reload, register, and execute (PTY run). Hot reload: in-memory
    catalog is the source of truth; reload() loads from file, register() updates
    in-memory only (or save() to persist).
    """

    def __init__(
        self,
        config_path: Path | None = None,
        initial_catalog: dict[str, Any] | None = None,
        workspace: Path | None = None,
    ):
        self._config_path = Path(config_path) if config_path else None
        self._workspace = Path(workspace) if workspace else None
        self._catalog: dict[str, dict[str, Any]] = {}
        if initial_catalog:
            for k, v in initial_catalog.items():
                self._catalog[k] = _entry_to_dict(v)

    def get_entry(self, key: str) -> dict[str, Any] | None:
        """Return the catalog entry for key, or None."""
        return self._catalog.get(key)

    def list_keys(self) -> list[str]:
        """Return all catalog keys (for tool schema / health)."""
        return list(self._catalog.keys())

    def get_spawn_hint(self) -> str | None:
        """Return a system prompt hint for the main agent to run catalog software via spawn.

        Returns None when the catalog is empty (no software installed yet).
        """
        keys = self.list_keys()
        if not keys:
            return None
        keys_str = ", ".join(keys)
        return (
            f"Installed catalog software: {keys_str}. "
            "To run any of them, use the **spawn** tool and give the subagent a clear task "
            "(e.g. 'Use software_exec with backend_key X and task Y'). "
            "The subagent has the software_exec tool. "
            "Do not tell users you cannot run installed software or that a delegate/CLI tool fails."
        )

    def get_catalog(self) -> dict[str, dict[str, Any]]:
        """Return the full in-memory catalog (e.g. for health warnings)."""
        return dict(self._catalog)

    def register(self, key: str, entry: dict[str, Any]) -> None:
        """Add or update an entry in the in-memory catalog (hot reload)."""
        self._catalog[key] = dict(entry)
        logger.info(f"Registered software in catalog: {key}")

    def unregister(self, key: str) -> None:
        """Remove an entry from the in-memory catalog (hot reload)."""
        self._catalog.pop(key, None)
        logger.info(f"Unregistered software from catalog: {key}")

    def reload(self) -> None:
        """Load catalog from config file into in-memory. No-op if no config_path."""
        if not self._config_path:
            return
        try:
            config = load_config(self._config_path)
            software = getattr(config.tools, "software", None) or {}
            self._catalog = {k: _entry_to_dict(v) for k, v in software.items()}
            logger.debug(
                f"Reloaded software catalog from {self._config_path} ({len(self._catalog)} entries)"
            )
        except Exception as e:
            logger.warning(f"Failed to reload software catalog: {e}")

    def save(self) -> None:
        """Persist in-memory catalog to config file. No-op if no config_path."""
        if not self._config_path:
            return
        try:
            existing: dict = {}
            if self._config_path.exists():
                try:
                    existing = _load_raw(self._config_path)
                except Exception:
                    pass
            tools = dict(existing.get("tools") or {})
            tools["software"] = dict(self._catalog)
            existing["tools"] = tools
            save_config(existing, self._config_path)
        except Exception as e:
            logger.warning(f"Failed to save software catalog: {e}")

    async def install(
        self,
        *,
        slug: str,
        install_type: str = "npm",
        package: str = "",
        command: str = "",
        name: str = "",
        description: str = "",
        skill_content: str = "",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        stdin: bool = False,
        post_install: dict | None = None,
    ) -> dict[str, Any]:
        """
        Run install (npm/pip/shell), persist entry to config, update in-memory.
        Returns a result dict for the admin API: ok, slug, message, logs,
        exit_code, verified, resolved_command.
        """
        key = slug_to_key(slug)
        cmd = _build_install_cmd(install_type, package)
        if not cmd:
            return {
                "ok": False,
                "slug": slug,
                "message": f"Unsupported install_type: {install_type}",
                "logs": "",
                "exit_code": 1,
                "verified": False,
                "resolved_command": command,
            }

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        exit_code = proc.returncode or 0

        out_text = stdout_bytes.decode("utf-8", errors="replace").strip()
        err_text = stderr_bytes.decode("utf-8", errors="replace").strip()
        full_logs = out_text
        if err_text:
            full_logs = f"{full_logs}\n--- stderr ---\n{err_text}" if full_logs else err_text

        if exit_code != 0:
            return {
                "ok": False,
                "slug": slug,
                "message": f"{install_type} install failed (exit {exit_code})",
                "logs": full_logs[-4000:],
                "exit_code": exit_code,
                "verified": False,
                "resolved_command": command,
            }

        resolved_command = await _find_binary(command, install_type)
        verified = resolved_command != command or bool(shutil.which(command))

        use_npx = (
            not verified
            and install_type == "npm"
            and package
            and (command in ("", resolved_command) or not shutil.which(command))
        )

        entry = {
            "name": name,
            "description": description,
            "command": "npx" if use_npx else resolved_command,
            "args": (["--yes", package] + (args or [])) if use_npx else (args or []),
            "env": env or {},
            "installed_via": install_type,
            "package": package,
            "stdin": stdin,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "verified": verified or use_npx,
        }
        if use_npx:
            entry["via_npx"] = True
        if post_install:
            entry["post_install"] = post_install
        self._catalog[key] = entry
        self.save()

        msg = out_text[:200] or "Installed."
        if not verified and command and not use_npx:
            msg += f" (warning: '{command}' not found in PATH after install)"
        elif use_npx:
            msg += " (will run via npx since binary not in PATH)"

        self._write_skill(key, entry, skill_content=skill_content)
        self._update_lock(key, entry)

        if post_install:
            try:
                await _run_post_install(post_install, install_type, extra_env=entry.get("env"))
                msg = (msg.rstrip(".") + ". Post-install started.").strip()
            except Exception as e:
                logger.warning(f"Post-install failed for '{key}': {e}")
                msg = (msg.rstrip(".") + f". Post-install failed: {e}").strip()

        return {
            "ok": True,
            "slug": slug,
            "message": msg,
            "logs": full_logs[-4000:],
            "exit_code": exit_code,
            "verified": verified or use_npx,
            "resolved_command": "npx" if use_npx else resolved_command,
        }

    async def uninstall(self, slug: str) -> dict[str, Any]:
        """
        Remove entry from config and in-memory; run npm/pip uninstall if applicable.
        Returns a result dict for the admin API.
        """
        key = slug_to_key(slug)
        entry = self._catalog.get(key)
        if not entry:
            try:
                config = load_config(self._config_path) if self._config_path else None
                if config:
                    software = getattr(config.tools, "software", None) or {}
                    entry = software.get(key) or software.get(slug)
                    if entry:
                        entry = _entry_to_dict(entry)
            except Exception:
                pass
        if not entry:
            raise FileNotFoundError(f"Software '{slug}' is not installed")

        package = _get_entry_attr(entry, "package", "")
        installed_via = _get_entry_attr(entry, "installed_via", "") or "npm"

        if not package:
            raise ValueError(f"No package name for software '{slug}'")

        uninstall_logs = ""
        uninstall_exit_code = 0

        if installed_via == "npm":
            proc = await asyncio.create_subprocess_exec(
                "npm",
                "uninstall",
                "-g",
                package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            uninstall_exit_code = proc.returncode or 0
            uninstall_logs = stdout_bytes.decode("utf-8", errors="replace").strip()
            if stderr_bytes:
                err_text = stderr_bytes.decode("utf-8", errors="replace").strip()
                uninstall_logs = (
                    f"{uninstall_logs}\n--- stderr ---\n{err_text}" if uninstall_logs else err_text
                )
        elif installed_via == "pip":
            proc = await asyncio.create_subprocess_exec(
                "pip",
                "uninstall",
                "--yes",
                package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            uninstall_exit_code = proc.returncode or 0
            uninstall_logs = stdout_bytes.decode("utf-8", errors="replace").strip()
            if stderr_bytes:
                err_text = stderr_bytes.decode("utf-8", errors="replace").strip()
                uninstall_logs = (
                    f"{uninstall_logs}\n--- stderr ---\n{err_text}" if uninstall_logs else err_text
                )

        if uninstall_exit_code != 0:
            return {
                "ok": False,
                "slug": slug,
                "message": f"{installed_via} uninstall failed (exit {uninstall_exit_code})",
                "logs": uninstall_logs[-4000:] if uninstall_logs else None,
                "exit_code": uninstall_exit_code,
            }

        self._catalog.pop(key, None)
        self._catalog.pop(slug, None)
        self.save()
        self._remove_skill(key)
        self._remove_from_lock(key)
        return {"ok": True, "slug": slug, "message": "Uninstalled."}

    async def execute(
        self,
        key: str,
        task: str,
        working_dir: str | Path | None = None,
        workspace: Path | None = None,
        max_output_chars: int = SOFTWARE_EXEC_MAX_OUTPUT_CHARS,
    ) -> str:
        """
        Run the installed software by key with the given task (PTY). Returns
        combined stdout/stderr (ANSI stripped). workspace is the default cwd
        when working_dir is not set.
        """
        entry = self._catalog.get(key)
        if not entry:
            hint = (
                f" Available: {', '.join(self.list_keys())}."
                if self._catalog
                else " No software installed."
            )
            return f"Error: unknown software key '{key}'." + hint

        command = _get_entry_attr(entry, "command")
        if not command:
            return "Error: no command configured for this software."

        args = _get_entry_attr(entry, "args") or []
        if not isinstance(args, list):
            args = []
        use_stdin = bool(_get_entry_attr(entry, "stdin"))
        timeout = int(_get_entry_attr(entry, "timeout") or 0)

        env = dict(os.environ)
        extra_env = _get_entry_attr(entry, "env") or {}
        if isinstance(extra_env, dict):
            env.update(extra_env)
        env.setdefault("TERM", "dumb")
        env["NO_COLOR"] = "1"
        env["CI"] = "true"

        try:
            install_type = _get_entry_attr(entry, "installed_via", "")
            command = await _find_binary(command, install_type, env=env)
        except Exception as e:
            return f"Error: {e!s}"

        cwd = (workspace or Path.cwd()).resolve()
        if working_dir:
            p = Path(working_dir)
            if p.is_absolute():
                cwd = p.resolve()
            else:
                cwd = (cwd / working_dir).resolve()
        if not cwd.exists() and workspace:
            cwd = workspace.resolve()

        full_cmd = [command] + list(args)
        if not use_stdin:
            full_cmd.append(task)
        stdin_data = task.encode("utf-8") if use_stdin else None

        try:
            combined = await _run_with_pty(full_cmd, str(cwd), env, stdin_data, timeout=timeout)
            if len(combined) > max_output_chars:
                combined = combined[:max_output_chars] + "\n... (output truncated)"
            return combined or "(no output)"
        except Exception as e:
            logger.exception(f"Software execute failed for key={key}")
            return f"Error: {e!s}"

    def _write_skill(self, key: str, entry: dict[str, Any], *, skill_content: str = "") -> None:
        """Write .agents/skills/<key>/SKILL.md so the agent gains the skill immediately."""
        if not self._workspace:
            return
        name = entry.get("name") or key
        description = entry.get("description") or f"Installed software: {name}"
        command = entry.get("command") or key
        args = entry.get("args") or []
        args_str = (" " + " ".join(str(a) for a in args)) if args else ""
        skill_dir = self._workspace / ".agents" / "skills" / key
        try:
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_file = skill_dir / "SKILL.md"
            if skill_content:
                body = skill_content.strip()
            else:
                body = (
                    f"{description}\n\n"
                    f"## Usage\n\n"
                    f"Run via the `software_exec` tool with key `{key}`.\n\n"
                    f"Command: `{command}{args_str}`\n"
                )
            content = (
                f"---\n"
                f"name: {name}\n"
                f"description: {description}\n"
                f'metadata: {{"clawbot":{{}}}}\n'
                f"---\n\n"
                f"# {name}\n\n"
                f"{body}\n"
            )
            skill_file.write_text(content, encoding="utf-8")
            logger.debug(f"Wrote skill file: {skill_file}")
        except Exception as e:
            logger.warning(f"Failed to write skill file for '{key}': {e}")

    def _remove_skill(self, key: str) -> None:
        """Remove .agents/skills/<key>/ on uninstall."""
        if not self._workspace:
            return
        skill_dir = self._workspace / ".agents" / "skills" / key
        if skill_dir.exists():
            try:
                shutil.rmtree(skill_dir)
                logger.debug(f"Removed skill dir: {skill_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove skill dir for '{key}': {e}")

    def _update_lock(self, key: str, entry: dict[str, Any]) -> None:
        """Add or update an entry in workspace/skills-lock.json."""
        if not self._workspace:
            return
        lock_path = self._workspace / "skills-lock.json"
        try:
            lock: dict[str, Any] = {}
            if lock_path.exists():
                try:
                    lock = json.loads(lock_path.read_text(encoding="utf-8"))
                except Exception:
                    lock = {}
            if not isinstance(lock.get("skills"), dict):
                lock["version"] = 1
                lock["skills"] = {}
            lock["skills"][key] = {
                "source": "catalog",
                "package": entry.get("package", ""),
                "command": entry.get("command", ""),
                "installed_at": entry.get("installed_at", ""),
            }
            lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
            logger.debug(f"Updated skills-lock.json for '{key}'")
        except Exception as e:
            logger.warning(f"Failed to update skills-lock.json for '{key}': {e}")

    def _remove_from_lock(self, key: str) -> None:
        """Remove an entry from workspace/skills-lock.json on uninstall."""
        if not self._workspace:
            return
        lock_path = self._workspace / "skills-lock.json"
        if not lock_path.exists():
            return
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            if isinstance(lock.get("skills"), dict):
                lock["skills"].pop(key, None)
                lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
                logger.debug(f"Removed '{key}' from skills-lock.json")
        except Exception as e:
            logger.warning(f"Failed to remove '{key}' from skills-lock.json: {e}")

    async def reinstall_missing(self) -> None:
        """Re-install software whose binaries are missing (e.g. after container restart).

        For each catalog entry whose command is no longer on PATH, runs the
        package manager again (with retries), re-resolves the binary path, and
        re-runs any post_install hook (e.g. to restart daemon processes).
        """
        if not self._config_path:
            return
        self.reload()
        if not self._catalog:
            return

        def is_available(cmd: str) -> bool:
            if not cmd:
                return False
            if os.path.isabs(cmd):
                return os.path.isfile(cmd) and os.access(cmd, os.X_OK)
            return shutil.which(cmd) is not None

        updated = False
        for key, entry in list(self._catalog.items()):
            cmd = _get_entry_attr(entry, "command", "")
            if is_available(cmd):
                continue

            package = _get_entry_attr(entry, "package", "")
            if not package:
                logger.warning("Software '%s' has no package info, cannot reinstall", key)
                continue

            install_type = _get_entry_attr(entry, "installed_via", "") or "npm"
            install_cmd = _build_install_cmd(install_type, package)
            if not install_cmd:
                logger.warning("Software '%s' has unsupported install_type '%s'", key, install_type)
                continue

            logger.info("Re-installing '%s' (%s %s) — binary missing", key, install_type, package)
            ok = await _run_install_with_retry(install_cmd, key)
            if not ok:
                continue

            base_cmd = cmd.rsplit("/", 1)[-1] if "/" in cmd else cmd
            resolved = await _find_binary(base_cmd, install_type)
            if resolved != cmd:
                entry["command"] = resolved
                updated = True
            logger.info("Software '%s' re-installed successfully", key)

            post_install = entry.get("post_install")
            if isinstance(post_install, dict):
                try:
                    await _run_post_install(post_install, install_type, extra_env=entry.get("env"))
                    logger.info("Started post-install for '%s'", key)
                except Exception as e:
                    logger.warning("Post-install failed for '%s' after reinstall: %s", key, e)

        if updated:
            self.save()
            logger.info("Updated catalog with resolved command paths after reinstall")
