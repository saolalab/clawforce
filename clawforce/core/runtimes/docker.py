"""Docker-based agent runtime: one agent per container.

Security model:
- Each agent runs in an isolated Docker container
- App-level restrictions (AgentFS, restrict_to_workspace) enforce
  workspace/profiles boundaries
- OS-level sandbox (bubblewrap) is disabled - Docker provides isolation
- Agents fetch secrets from vault API at runtime (not stored on disk)

Communication: agents connect back to admin via WebSocket (control plane).
No HTTP port mapping is needed.

Docker connectivity:
- Set DOCKER_HOST to a TCP endpoint (tcp://host:2375) for remote daemon access.
- Falls back to the default Unix socket (/var/run/docker.sock) when unset.
- TCP is preferred in containerised deployments; avoids mounting the Docker
  socket and the associated security surface.
"""

import asyncio
import json
import logging
import os
import socket as socket_mod
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import WebSocket, WebSocketDisconnect

from clawforce.core.database import get_database
from clawforce.core.domain.agent import control_plane_overrides
from clawforce.core.domain.runtime import AgentRuntimeError
from clawforce.core.runtimes._worker_runtime import WorkerRuntimeBase
from clawforce.core.services.workspace_service import AGENTS_DIR
from clawforce.core.storage import StorageBackend
from clawforce.core.store.agent_config import AgentConfigStore
from clawforce.core.store.agent_variables import AgentVariablesStore
from clawforce.deps import get_fernet
from clawlib.config.schema import DockerSecurityConfig
from clawlib.registry import get_software_registry

logger = logging.getLogger(__name__)

DOCKER_HOST = os.environ.get("DOCKER_HOST", "")
DOCKER_IMAGE = os.environ.get("AGENT_IMAGE", "ghcr.io/saolalab/clawforce:latest")
AGENT_DOCKER_MEM_LIMIT = os.environ.get("AGENT_DOCKER_MEM_LIMIT", "2g")
AGENT_DOCKER_CPU_QUOTA = int(os.environ.get("AGENT_DOCKER_CPU_QUOTA", "100000"))
AGENT_DOCKER_CPU_PERIOD = int(os.environ.get("AGENT_DOCKER_CPU_PERIOD", "100000"))

PERMISSIVE_PRESET: dict[str, Any] = {
    "mem_limit": AGENT_DOCKER_MEM_LIMIT,
    "cpu_quota": AGENT_DOCKER_CPU_QUOTA,
    "cpu_period": AGENT_DOCKER_CPU_PERIOD,
    "security_opt": ["no-new-privileges:true"],
    "cap_drop": ["ALL"],
    "cap_add": ["NET_BIND_SERVICE"],
    "read_only": False,
    "network_mode": None,
    "pids_limit": None,
    "tmpfs": None,
}

SANDBOXED_PRESET: dict[str, Any] = {
    "mem_limit": "1g",
    "cpu_quota": 100000,
    "cpu_period": 100000,
    "security_opt": ["no-new-privileges:true"],
    "cap_drop": ["ALL"],
    "cap_add": [],
    "read_only": True,
    "network_mode": "none",
    "pids_limit": 256,
    "tmpfs": {"/tmp": "size=2g"},  # 2g for npm/pip install temp space
}

PRIVILEGED_PRESET: dict[str, Any] = {
    "mem_limit": AGENT_DOCKER_MEM_LIMIT,
    "cpu_quota": AGENT_DOCKER_CPU_QUOTA,
    "cpu_period": AGENT_DOCKER_CPU_PERIOD,
    "security_opt": [],
    "cap_drop": [],
    "cap_add": [],
    "read_only": False,
    "network_mode": None,
    "pids_limit": None,
    "tmpfs": None,
}


def get_docker_presets() -> dict[str, dict[str, Any]]:
    """Return permissive, sandboxed, and privileged presets for UI and API."""
    return {
        "permissive": dict(PERMISSIVE_PRESET),
        "sandboxed": dict(SANDBOXED_PRESET),
        "privileged": dict(PRIVILEGED_PRESET),
    }


def _resolve_docker_run_kwargs(cfg: DockerSecurityConfig) -> dict[str, Any]:
    """Build containers.run() kwargs from security config (preset + overrides)."""
    level = (cfg.level or "permissive").lower()
    if level == "sandboxed":
        preset = SANDBOXED_PRESET
    elif level == "privileged":
        preset = PRIVILEGED_PRESET
    else:
        preset = PERMISSIVE_PRESET
    out: dict[str, Any] = dict(preset)
    if cfg.mem_limit is not None:
        out["mem_limit"] = cfg.mem_limit
    if cfg.cpu_quota is not None:
        out["cpu_quota"] = cfg.cpu_quota
    if cfg.cpu_period is not None:
        out["cpu_period"] = cfg.cpu_period
    if cfg.read_only is not None:
        out["read_only"] = cfg.read_only
    if cfg.network_mode is not None:
        out["network_mode"] = cfg.network_mode if cfg.network_mode else None
    if cfg.pids_limit is not None:
        out["pids_limit"] = cfg.pids_limit if cfg.pids_limit else None
    return out


def _container_name(agent_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in agent_id)
    return f"clawbot-agent-{safe}"[:64]


def _is_remote_daemon() -> bool:
    """True when DOCKER_HOST points to a non-local endpoint (tcp://, ssh://)."""
    if not DOCKER_HOST:
        return False
    return DOCKER_HOST.startswith("tcp://") or DOCKER_HOST.startswith("ssh://")


def _self_container_info(client) -> dict | None:
    """Inspect the current container's metadata (when running inside Docker).

    Returns None when the daemon is remote (admin and workers are on different
    hosts, so self-inspection is meaningless) or when we're not in Docker.
    """
    if _is_remote_daemon():
        return None
    try:
        hostname = socket_mod.gethostname()
        return client.containers.get(hostname).attrs
    except Exception:
        return None


def _detect_host_mount_source(client, container_path: str) -> str | None:
    """Auto-detect the host source path for a given mount destination.

    When the control plane runs inside Docker, we inspect our own container's
    mounts to find what host path is mapped to *container_path* (e.g. ``/data``).
    This lets us build correct bind-mount paths for agent worker containers
    without requiring the user to set ``AGENT_STORAGE_HOST_PATH``.
    """
    info = _self_container_info(client)
    if not info:
        return None
    try:
        for mount in info.get("Mounts", []):
            if mount.get("Destination") == container_path:
                source = mount.get("Source")
                logger.info(f"Auto-detected host mount: {container_path} -> {source}")
                return source
        logger.debug(
            f"No mount found for {container_path} in container {info.get('Config', {}).get('Hostname', '?')}"
        )
    except Exception as exc:
        logger.debug(f"Could not auto-detect host mount: {exc}")
    return None


def _detect_admin_network(client) -> str | None:
    """Return the admin container's first network name so agent can join it."""
    info = _self_container_info(client)
    if not info:
        return None
    try:
        networks = info.get("NetworkSettings", {}).get("Networks", {})
        return next(iter(networks)) if networks else None
    except Exception:
        return None


def _detect_admin_internal_url(client, internal_port: int = 8080) -> str | None:
    """Auto-detect the admin container's bridge network IP for worker connectivity.

    When both admin and worker run as Docker containers on the same bridge
    network, workers can reach the admin via the container IP directly.  This
    avoids host port-mapping mismatches (e.g. admin published on port 9090 but
    ADMIN_PUBLIC_URL still says 8080).
    """
    info = _self_container_info(client)
    if not info:
        return None
    try:
        networks = info.get("NetworkSettings", {}).get("Networks", {})
        for net_name, net_info in networks.items():
            ip = net_info.get("IPAddress")
            if ip:
                url = f"http://{ip}:{internal_port}"
                logger.info(
                    f"Auto-detected admin URL via Docker bridge: {url} (network={net_name})"
                )
                return url
    except Exception as exc:
        logger.debug(f"Could not auto-detect admin internal URL: {exc}")
    return None


def _software_port_env(installed_software: dict, registry) -> dict[str, str]:
    """Inject {SOFTWARE_ID}_PORT for any installed software with a declared run.port."""
    env: dict[str, str] = {}
    for slug in installed_software:
        catalog_entry = registry.get_entry(slug) or {}
        port = (catalog_entry.get("run") or {}).get("port")
        if port is not None:
            env_key = slug.upper().replace("-", "_") + "_PORT"
            env[env_key] = str(port)
    return env


def _agent_docker_security(storage: StorageBackend, base_path: str) -> DockerSecurityConfig:
    """Read agent's security.docker from .config/agent.json; fall back to defaults."""
    path = f"{AGENTS_DIR}/{base_path}/.config/agent.json"
    try:
        raw = json.loads(storage.read_sync(path).decode("utf-8"))
    except (FileNotFoundError, ValueError, TypeError, KeyError):
        return DockerSecurityConfig()
    docker_raw = (raw.get("security") or {}).get("docker")
    if not docker_raw or not isinstance(docker_raw, dict):
        return DockerSecurityConfig()
    try:
        return DockerSecurityConfig.model_validate(docker_raw)
    except Exception:
        return DockerSecurityConfig()


def _build_docker_client():
    """Create a Docker client with explicit host resolution.

    Priority:
      1. DOCKER_HOST env var (supports tcp://, unix://, ssh://)
      2. Platform default (Unix socket on Linux/macOS, named pipe on Windows)

    Validates connectivity eagerly so failures surface at startup.
    """
    try:
        import docker
    except ImportError as e:
        raise RuntimeError(
            "Docker runtime requires the docker package. Install with: pip install docker>=7.0.0"
        ) from e

    if DOCKER_HOST:
        client = docker.DockerClient(base_url=DOCKER_HOST)
        logger.info(f"Docker client configured with explicit host: {DOCKER_HOST}")
    else:
        client = docker.from_env()
        logger.info(
            "Docker client using platform default (DOCKER_HOST not set; "
            "set DOCKER_HOST=tcp://host:2375 for TCP)"
        )

    try:
        client.ping()
    except Exception as exc:
        hint = (
            f"DOCKER_HOST={DOCKER_HOST}"
            if DOCKER_HOST
            else "default Unix socket /var/run/docker.sock"
        )
        raise AgentRuntimeError(
            f"Cannot reach Docker daemon ({hint}). "
            "Ensure the daemon is running and the endpoint is accessible. "
            "For TCP: set DOCKER_HOST=tcp://<host>:2375 and ensure the Docker "
            "daemon listens on TCP (dockerd -H tcp://0.0.0.0:2375)."
        ) from exc

    info = client.version()
    logger.info(
        "Docker daemon connected — API v%s, Engine %s",
        info.get("ApiVersion", "?"),
        info.get("Version", "?"),
    )
    return client


class DockerRuntime(WorkerRuntimeBase):
    """Run one agent per Docker container."""

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
        self._docker = None

    def _client(self):
        if self._docker is None:
            self._docker = _build_docker_client()
        return self._docker

    def get_docker_presets(self) -> dict[str, dict[str, Any]]:
        """Return permissive and sandboxed security presets for API/UI."""
        return get_docker_presets()

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

        try:
            name = _container_name(agent_id)

            cp = control_plane_overrides(agent)
            base_path = agent.base_path or agent_id
            docker_cfg = _agent_docker_security(self._storage, base_path)
            run_kwargs = _resolve_docker_run_kwargs(docker_cfg)

            admin_url: str = cp["admin_url"]
            remote = _is_remote_daemon()

            _uses_local = (
                "host.docker.internal" in admin_url
                or "127.0.0.1" in admin_url
                or "localhost" in admin_url
            )
            if remote and _uses_local:
                logger.warning(
                    "DOCKER_HOST is remote (%s) but ADMIN_PUBLIC_URL is %s — "
                    "worker containers on the remote host cannot reach this address. "
                    "Set ADMIN_PUBLIC_URL to an IP/hostname reachable from the remote Docker host.",
                    DOCKER_HOST,
                    admin_url,
                )
            elif _uses_local:
                # Mac/Windows: host.docker.internal works natively.
                # Linux: use host.docker.internal + extra_hosts (host-gateway) for cross-platform support.
                if "host.docker.internal" not in admin_url:
                    detected = _detect_admin_internal_url(self._client())
                    if detected:
                        logger.info(
                            "Using auto-detected admin URL %s (instead of %s)",
                            detected,
                            admin_url,
                        )
                        admin_url = detected
                    elif "127.0.0.1" in admin_url or "localhost" in admin_url:
                        parsed = urlparse(admin_url)
                        port = parsed.port or 8080
                        netloc = f"host.docker.internal:{port}" if port else "host.docker.internal"
                        admin_url = parsed._replace(netloc=netloc).geturl()
                        logger.info(
                            "Using host.docker.internal:%s (localhost unreachable from containers)",
                            port,
                        )

            storage_root = str(
                getattr(self._storage, "root", None)
                or os.environ.get("ADMIN_STORAGE_ROOT", "/data")
            )
            agent_host_base = os.environ.get("AGENT_STORAGE_HOST_PATH")
            if not agent_host_base:
                agent_host_base = (
                    _detect_host_mount_source(self._client(), storage_root) or storage_root
                )
            if remote and not os.environ.get("AGENT_STORAGE_HOST_PATH"):
                logger.warning(
                    "DOCKER_HOST is remote (%s) but AGENT_STORAGE_HOST_PATH is not set. "
                    "The storage path '%s' must exist on the remote Docker host. "
                    "Set AGENT_STORAGE_HOST_PATH to the correct path on the remote host.",
                    DOCKER_HOST,
                    agent_host_base,
                )
            logger.info(f"Agent host base: {agent_host_base} (storage_root={storage_root})")
            agent_root_in_container = "/agent"

            agent_config_store = AgentConfigStore(get_database(), fernet=get_fernet())
            agent_config = agent_config_store.get_config(agent_id) or {}
            installed_software = (agent_config.get("tools") or {}).get("software") or {}
            extra_ports = _software_port_env(installed_software, get_software_registry())

            env = {
                "AGENT_ID": agent_id,
                "AGENT_ROOT": agent_root_in_container,
                "ADMIN_URL": admin_url,
                "AGENT_TOKEN": cp["agent_token"],
                **extra_ports,
                "AGENT_LOG_LEVEL": docker_cfg.log_level
                or os.environ.get("AGENT_LOG_LEVEL", "INFO"),
                "PYTHONUNBUFFERED": "1",
            }

            variables_store = AgentVariablesStore(get_database())
            variables = variables_store.get_variables(agent_id)
            for key, value in variables.items():
                if key and value:
                    env[key] = str(value)

            needs_host_gateway = "host.docker.internal" in admin_url
            admin_network = None if remote else _detect_admin_network(self._client())

            def _run():
                client = self._client()
                try:
                    client.images.get(DOCKER_IMAGE)
                except Exception:
                    logger.info(
                        "Image %s not found locally, pulling from registry...", DOCKER_IMAGE
                    )
                    try:
                        client.images.pull(DOCKER_IMAGE)
                        logger.info(f"Successfully pulled image {DOCKER_IMAGE}")
                    except Exception as pull_exc:
                        raise AgentRuntimeError(
                            f"Docker image {DOCKER_IMAGE} not found locally and pull failed: {pull_exc}. "
                            "Ensure the image is available in the registry and you are authenticated "
                            "(run: docker login ghcr.io)."
                        ) from pull_exc
                try:
                    old = client.containers.get(name)
                    old.remove(force=True)
                except Exception:
                    pass

                agent_path_host = (Path(agent_host_base) / AGENTS_DIR / base_path).resolve()
                if not remote:
                    agent_path_host.mkdir(parents=True, exist_ok=True)
                volumes = [f"{agent_path_host}:/agent:rw"]

                # Default CWD to agent workspace so exec/terminal and ad-hoc shells start there
                workspace_in_container = f"{agent_root_in_container}/workspace"
                kwargs: dict[str, Any] = {
                    "image": DOCKER_IMAGE,
                    "command": ["python", "-m", "clawbot.worker.app"],
                    "detach": True,
                    "name": name,
                    "environment": env,
                    "volumes": volumes,
                    "working_dir": workspace_in_container,
                    "remove": False,
                    **{k: v for k, v in run_kwargs.items() if v is not None},
                }

                if needs_host_gateway:
                    kwargs["extra_hosts"] = {"host.docker.internal": "host-gateway"}
                if admin_network and kwargs.get("network_mode") is None:
                    kwargs["network"] = admin_network

                return client.containers.run(**kwargs)

            loop = asyncio.get_running_loop()
            container = await loop.run_in_executor(None, _run)
            self._running[agent_id] = {"container": container}
            self._store.update_agent(agent_id, status="connecting")
            await asyncio.sleep(1.0)
        except AgentRuntimeError:
            self._store.update_agent(agent_id, status="stopped")
            raise
        except Exception as exc:
            self._store.update_agent(agent_id, status="stopped")
            logger.exception(f"Failed to start agent {agent_id}")
            raise AgentRuntimeError(f"Failed to start agent: {exc!s}") from exc

    async def _cleanup_entry(self, agent_id: str) -> None:
        """Remove a dead container from _running. Allows restart after crash."""
        entry = self._running.pop(agent_id, None)
        if not entry:
            return
        container = entry.get("container")
        if container:

            def _remove():
                try:
                    container.reload()
                    if container.status != "running":
                        container.remove(force=True)
                except Exception:
                    pass

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _remove)
        self._store.update_agent(agent_id, status="stopped")

    async def stop_agent(self, agent_id: str) -> None:
        if agent_id not in self._running:
            self._store.update_agent(agent_id, status="stopped")
            return
        entry = self._running.pop(agent_id)
        container = entry["container"]

        def _stop():
            try:
                container.stop(timeout=5)
            except Exception:
                pass
            try:
                container.remove()
            except Exception:
                pass

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _stop)
        self._store.update_agent(agent_id, status="stopped")

    async def _is_worker_alive(self, agent_id: str) -> bool:
        container = self._running[agent_id]["container"]
        try:
            container.reload()
            return container.status == "running"
        except Exception:
            return False

    def _storage_prefix(self, agent_id: str) -> str:
        """Return storage prefix for agent (agents/{base_path}/)."""
        agent = self._store.get_agent(agent_id)
        base_path = (agent.base_path or agent_id) if agent else agent_id
        return f"{AGENTS_DIR}/{base_path}"

    async def _is_container_running(self, agent_id: str) -> bool:
        """True if agent container exists and is running (may repopulate _running)."""
        if agent_id in self._running:
            return await self._is_worker_alive(agent_id)
        name = _container_name(agent_id)
        loop = asyncio.get_running_loop()

        def _check():
            try:
                container = self._client().containers.get(name)
                return container if container.status == "running" else None
            except Exception:
                return None

        try:
            container = await asyncio.wait_for(
                loop.run_in_executor(None, _check),
                timeout=5.0,
            )
            if container:
                self._running[agent_id] = {"container": container}
                return True
        except asyncio.TimeoutError:
            logger.debug(f"Docker containers.get({name}) timed out")
        return False

    async def _list_from_storage(self, agent_id: str, root: str) -> list[str]:
        """List files from storage when WebSocket is unavailable (Docker bind-mount fallback)."""
        prefix = f"{self._storage_prefix(agent_id)}/{root}"
        try:
            return await self._storage.list_dir(prefix)
        except Exception:
            return []

    async def _read_from_storage(self, agent_id: str, root: str, path: str) -> str | None:
        """Read file from storage when WebSocket is unavailable."""
        full = f"{self._storage_prefix(agent_id)}/{root}/{path}"
        try:
            data = await self._storage.read(full)
            return data.decode("utf-8", errors="replace")
        except FileNotFoundError:
            return None
        except Exception:
            return None

    async def list_workspace(self, agent_id: str) -> list[str]:
        if self._is_ws_connected(agent_id):
            return await super().list_workspace(agent_id)
        if await self._is_container_running(agent_id):
            logger.debug(
                "Agent %s not connected; using storage fallback for list_workspace", agent_id
            )
            return await self._list_from_storage(agent_id, "workspace")
        raise AgentRuntimeError(f"Agent {agent_id} is not connected")

    async def list_profile(self, agent_id: str) -> list[str]:
        if self._is_ws_connected(agent_id):
            return await super().list_profile(agent_id)
        if await self._is_container_running(agent_id):
            logger.debug(
                "Agent %s not connected; using storage fallback for list_profile", agent_id
            )
            return await self._list_from_storage(agent_id, "profiles")
        raise AgentRuntimeError(f"Agent {agent_id} is not connected")

    async def read_workspace_file(self, agent_id: str, path: str) -> str | None:
        if self._is_ws_connected(agent_id):
            return await super().read_workspace_file(agent_id, path)
        if await self._is_container_running(agent_id):
            return await self._read_from_storage(agent_id, "workspace", path)
        raise AgentRuntimeError(f"Agent {agent_id} is not connected")

    async def read_profile_file(self, agent_id: str, path: str) -> str | None:
        if self._is_ws_connected(agent_id):
            return await super().read_profile_file(agent_id, path)
        if await self._is_container_running(agent_id):
            return await self._read_from_storage(agent_id, "profiles", path)
        raise AgentRuntimeError(f"Agent {agent_id} is not connected")

    def supports_terminal(self) -> bool:
        return True

    def get_terminal_target(self, agent_id: str) -> tuple[str, Any] | None:
        if agent_id in self._running:
            return ("docker", self._running[agent_id]["container"])
        name = _container_name(agent_id)
        try:
            container = self._client().containers.get(name)
            if container.status == "running":
                self._running[agent_id] = {"container": container}
                return ("docker", container)
        except Exception:
            pass
        return None

    def get_container_logs(self, agent_id: str, tail: int = 200) -> str:
        """Return the last *tail* lines of the container logs."""
        if agent_id not in self._running:
            name = _container_name(agent_id)
            try:
                container = self._client().containers.get(name)
            except Exception as exc:
                return f"Container {name!r} not found or not accessible: {exc}\n"
        else:
            container = self._running[agent_id]["container"]
        try:
            logs = container.logs(tail=tail, timestamps=False).decode("utf-8", errors="replace")
            return logs
        except Exception:
            return ""

    def stream_container_logs(self, agent_id: str, tail: int = 100):
        """Generator that yields log lines from the container (like `docker logs -f`)."""
        if agent_id not in self._running:
            name = _container_name(agent_id)
            try:
                container = self._client().containers.get(name)
            except Exception as exc:
                yield f"Container {name!r} not found or not accessible: {exc}"
                return
        else:
            container = self._running[agent_id]["container"]
        try:
            for line in container.logs(stream=True, follow=True, tail=tail, timestamps=False):
                yield line.decode("utf-8", errors="replace").rstrip("\n")
        except Exception:
            return


def _unwrap_docker_socket(sock: Any) -> socket_mod.socket:
    """Extract a raw socket.socket from the object returned by exec_start(socket=True)."""
    raw = sock
    if hasattr(raw, "_sock"):
        raw = raw._sock
    if callable(getattr(raw, "get_raw_connection", None)):
        raw = raw.get_raw_connection()
    if isinstance(raw, socket_mod.socket):
        return raw
    if hasattr(raw, "_sock") and isinstance(raw._sock, socket_mod.socket):
        return raw._sock
    raise TypeError(
        f"Cannot extract raw socket from docker exec result: got {type(raw).__module__}.{type(raw).__qualname__}."
    )


async def bridge_docker_terminal(websocket: WebSocket, container: Any, agent_id: str) -> None:
    """Bridge WebSocket <-> Docker exec (interactive shell). Used by terminal API."""
    try:
        import docker  # noqa: F401
    except ImportError:
        await websocket.send_json({"type": "error", "data": "Docker SDK not installed"})
        return

    api = container.client.api
    cmd = ["/bin/bash", "-i"] if os.path.exists("/bin/bash") else ["/bin/sh", "-i"]
    try:
        exec_create_resp = api.exec_create(container.id, cmd, stdin=True, tty=True)
        exec_id = exec_create_resp.get("Id")
        if not exec_id:
            await websocket.send_json({"type": "error", "data": "Exec create failed"})
            return
        sock = api.exec_start(exec_id, tty=True, socket=True)
    except Exception as e:
        logger.exception(f"Docker exec failed for agent {agent_id}")
        await websocket.send_json({"type": "error", "data": str(e)})
        return

    if sock is None:
        await websocket.send_json({"type": "error", "data": "Exec socket unavailable"})
        return

    try:
        raw = _unwrap_docker_socket(sock)
    except TypeError as e:
        logger.error(f"Socket extraction failed for agent {agent_id}: {e}")
        await websocket.send_json({"type": "error", "data": str(e)})
        return

    loop = asyncio.get_running_loop()
    closed = asyncio.Event()

    async def read_docker_and_forward() -> None:
        try:
            while not closed.is_set():
                try:
                    data = await loop.run_in_executor(None, raw.recv, 4096)
                except (OSError, ConnectionError):
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

    async def forward_websocket_to_docker() -> None:
        try:
            while not closed.is_set():
                try:
                    msg = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                except asyncio.TimeoutError:
                    continue
                except WebSocketDisconnect:
                    break
                msg_type = msg.get("type")
                if msg_type == "input":
                    data = msg.get("data", "")
                    if isinstance(data, str):
                        data = data.encode("utf-8")
                    if data:
                        await loop.run_in_executor(None, raw.sendall, data)
                elif msg_type == "resize" and exec_id:
                    cols = msg.get("cols", 80)
                    rows = msg.get("rows", 24)
                    try:
                        api.exec_resize(exec_id, height=rows, width=cols)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass
        finally:
            closed.set()

    try:
        read_task = asyncio.create_task(read_docker_and_forward())
        write_task = asyncio.create_task(forward_websocket_to_docker())
        await asyncio.gather(read_task, write_task)
    finally:
        closed.set()
        try:
            raw.close()
        except Exception:
            pass
