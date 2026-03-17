"""Local agent runtime: one agent per subprocess (co-located, shared filesystem).

The local runtime runs the agent as a child process on the same machine.
Admin and agent share the filesystem, so:
- Admin creates the log directory and captures stdout/stderr to a log file.
- Admin can read the log file for the process-logs API.
- Terminal API spawns a shell in the agent's workspace directory.

These are inherent to the "local subprocess" model — a remote runtime backend
would not share a filesystem and would use WebSocket-based log streaming.
"""

import asyncio
import logging
import os
import pty
import select
import struct
import subprocess
import sys
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from clawforce.core.database import get_database
from clawforce.core.domain.agent import control_plane_overrides
from clawforce.core.domain.runtime import AgentRuntimeError
from clawforce.core.runtimes._worker_runtime import WorkerRuntimeBase
from clawforce.core.services.workspace_service import AGENTS_DIR
from clawforce.core.storage import StorageBackend, get_storage_root
from clawforce.core.store.agent_variables import AgentVariablesStore

logger = logging.getLogger(__name__)


class LocalRuntime(WorkerRuntimeBase):
    """Run one agent per subprocess."""

    def __init__(
        self,
        storage: StorageBackend | None = None,
        ws_manager=None,
        activity_registry=None,
    ) -> None:
        super().__init__(
            storage=storage,
            ws_manager=ws_manager,
            activity_registry=activity_registry,
        )

    async def start_agent(self, agent_id: str) -> None:
        if agent_id in self._running:
            if await self._is_worker_alive(agent_id):
                raise AgentRuntimeError(f"Agent {agent_id} is already running")
            await self._cleanup_entry(agent_id)
        agent = self._store.get_agent(agent_id)
        if not agent:
            raise AgentRuntimeError(f"Agent {agent_id} not found in store")
        if not agent.enabled:
            raise AgentRuntimeError(f"Agent {agent_id} is disabled")

        self._store.update_agent(agent_id, status="provisioning")

        root = get_storage_root(self._storage)
        base_path = agent.base_path or agent_id
        agent_root = root / AGENTS_DIR / base_path

        cp = control_plane_overrides(agent)

        logs_dir = agent_root / ".logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = logs_dir / "worker.log"
        log_fh = open(log_file_path, "a", buffering=1, encoding="utf-8")

        env = os.environ.copy()
        env["AGENT_ID"] = agent_id
        env["AGENT_ROOT"] = str(agent_root)
        env["ADMIN_URL"] = cp["admin_url"]
        env["AGENT_TOKEN"] = cp["agent_token"]
        env["PYTHONUNBUFFERED"] = "1"

        variables_store = AgentVariablesStore(get_database())
        variables = variables_store.get_variables(agent_id)
        for key, value in variables.items():
            if key and value:
                env[key] = str(value)

        proc = subprocess.Popen(
            [sys.executable, "-m", "clawbot.worker.app"],
            env=env,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
        )
        self._running[agent_id] = {
            "process": proc,
            "log_file": log_fh,
            "log_path": log_file_path,
        }
        self._store.update_agent(agent_id, status="connecting")
        logger.info(
            "Started worker subprocess pid=%s for agent %s (log: %s)",
            proc.pid,
            agent_id,
            log_file_path,
        )
        await asyncio.sleep(0.5)

        if proc.poll() is not None:
            log_fh.close()
            tail = self._tail_log(log_file_path, 40)
            self._running.pop(agent_id, None)
            self._store.update_agent(agent_id, status="failed")
            logger.error(
                "Worker for agent %s exited immediately (code=%s):\n%s",
                agent_id,
                proc.returncode,
                tail,
            )
            raise AgentRuntimeError(
                f"Worker process exited immediately (code={proc.returncode}):\n{tail[:500]}"
            )

    async def stop_agent(self, agent_id: str) -> None:
        if agent_id not in self._running:
            self._store.update_agent(agent_id, status="stopped")
            return
        entry = self._running.pop(agent_id)
        proc = entry["process"]
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        log_fh = entry.get("log_file")
        if log_fh:
            log_fh.close()
        self._store.update_agent(agent_id, status="stopped")

    async def _cleanup_entry(self, agent_id: str) -> None:
        entry = self._running.pop(agent_id, None)
        if not entry:
            return
        log_fh = entry.get("log_file")
        if log_fh:
            log_fh.close()

    async def _is_worker_alive(self, agent_id: str) -> bool:
        proc = self._running[agent_id]["process"]
        return proc.poll() is None

    def get_log_path(self, agent_id: str):
        """Return the worker log file path for an agent (running or not)."""
        entry = self._running.get(agent_id)
        if entry and "log_path" in entry:
            return entry["log_path"]
        agent = self._store.get_agent(agent_id)
        if agent:
            root = get_storage_root(self._storage)
            base_path = agent.base_path or agent_id
            return root / AGENTS_DIR / base_path / ".logs" / "worker.log"
        return None

    def supports_terminal(self) -> bool:
        return True

    def get_terminal_target(self, agent_id: str) -> tuple[str, Any] | None:
        if agent_id not in self._running:
            return None
        root = get_storage_root(self._storage)
        agent = self._store.get_agent(agent_id)
        base_path = (agent.base_path or agent_id) if agent else agent_id
        agent_root = str(root / AGENTS_DIR / base_path)
        if not os.path.isdir(agent_root):
            agent_root = str(root)
        return ("local", agent_root)

    @staticmethod
    def _tail_log(path, lines: int = 40) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            return "".join(all_lines[-lines:])
        except Exception:
            return ""


async def bridge_local_terminal(websocket: WebSocket, agent_id: str, agent_root: str) -> None:
    """Bridge WebSocket to a local PTY shell in the agent's workspace. Used by terminal API."""
    master, slave = pty.openpty()
    env = os.environ.copy()
    env["AGENT_ID"] = agent_id
    env["HOME"] = agent_root
    env["PWD"] = agent_root

    try:
        pid = os.fork()
    except OSError as e:
        await websocket.send_json({"type": "error", "data": f"fork failed: {e}"})
        return

    if pid == 0:
        os.close(master)
        os.chdir(agent_root)
        os.setsid()
        os.dup2(slave, 0)
        os.dup2(slave, 1)
        os.dup2(slave, 2)
        if slave > 2:
            os.close(slave)
        cmd = ["/bin/bash", "-i"] if os.path.exists("/bin/bash") else ["/bin/sh", "-i"]
        os.execvpe(cmd[0], cmd, env)
        sys.exit(127)

    os.close(slave)
    loop = asyncio.get_running_loop()
    closed = asyncio.Event()

    async def read_pty_and_forward() -> None:
        try:
            while not closed.is_set():
                try:
                    r, _, _ = await loop.run_in_executor(
                        None, lambda: select.select([master], [], [], 0.5)
                    )
                except Exception:
                    break
                if not r:
                    continue
                try:
                    data = await loop.run_in_executor(None, lambda: os.read(master, 4096))
                except Exception:
                    break
                if not data:
                    break
                try:
                    await websocket.send_json(
                        {"type": "output", "data": data.decode("utf-8", errors="replace")}
                    )
                except Exception:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            closed.set()

    async def forward_websocket_to_pty() -> None:
        try:
            while not closed.is_set():
                try:
                    msg = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                except asyncio.TimeoutError:
                    continue
                except WebSocketDisconnect:
                    break
                if msg.get("type") == "input":
                    data = msg.get("data", "")
                    if isinstance(data, str):
                        data = data.encode("utf-8")
                    if data:
                        await loop.run_in_executor(None, lambda: os.write(master, data))
                elif msg.get("type") == "resize":
                    try:
                        import fcntl
                        import termios

                        cols = msg.get("cols", 80)
                        rows = msg.get("rows", 24)
                        size = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(master, termios.TIOCSWINSZ, size)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass
        finally:
            closed.set()

    try:
        read_task = asyncio.create_task(read_pty_and_forward())
        write_task = asyncio.create_task(forward_websocket_to_pty())
        await asyncio.gather(read_task, write_task)
    finally:
        closed.set()
        try:
            os.close(master)
        except Exception:
            pass
        try:
            os.waitpid(pid, 0)
        except Exception:
            pass
