"""Kubernetes-based agent runtime: one agent per pod (k3s or any k8s cluster).

Uses in-cluster config when running inside k3s, or KUBECONFIG / k3s default
kubeconfig otherwise.

Connectivity:
- Set ADMIN_PUBLIC_URL to the admin URL reachable by agent pods.
  In k3s, defaults to http://clawforce.<namespace>.svc.cluster.local:8080.
- Set K8S_NAMESPACE to customize the namespace (default: clawforce).

Storage:
- Set AGENT_STORAGE_HOST_PATH to the host directory mounted at ADMIN_STORAGE_ROOT
  inside the admin pod.  Auto-detected from the admin pod's volume spec if unset.
"""

import asyncio
import json
import logging
import os
import socket as socket_mod
from pathlib import Path
from typing import Any

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
from clawlib.config.schema import K8sSecurityConfig
from clawlib.registry import get_software_registry

logger = logging.getLogger(__name__)

K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "clawforce")
K8S_IMAGE = os.environ.get("AGENT_IMAGE", "ghcr.io/saolalab/clawforce:latest")
K8S_IMAGE_PULL_POLICY = os.environ.get("AGENT_IMAGE_PULL_POLICY", "IfNotPresent")
# Default admin URL via k8s service DNS (used when ADMIN_PUBLIC_URL is localhost/127.0.0.1)
K8S_ADMIN_SERVICE_URL = os.environ.get(
    "K8S_ADMIN_SERVICE_URL",
    f"http://clawforce.{K8S_NAMESPACE}.svc.cluster.local:8080",
)

# Security presets expressed as K8sSecurityConfig overrides
PERMISSIVE_PRESET: dict[str, Any] = {
    "mem_limit": os.environ.get("AGENT_MEM_LIMIT", "2Gi"),
    "cpu_limit": os.environ.get("AGENT_CPU_LIMIT", "1"),
    "mem_request": "256Mi",
    "cpu_request": "100m",
    "allow_privilege_escalation": False,
    "cap_drop": ["ALL"],
    "cap_add": ["NET_BIND_SERVICE"],
    "read_only": False,
    "host_network": False,
    "pids_limit": None,
    "tmpfs": None,
}

SANDBOXED_PRESET: dict[str, Any] = {
    "mem_limit": "1Gi",
    "cpu_limit": "1",
    "mem_request": "128Mi",
    "cpu_request": "100m",
    "allow_privilege_escalation": False,
    "cap_drop": ["ALL"],
    "cap_add": [],
    "read_only": True,
    "host_network": False,
    "pids_limit": 256,
    "tmpfs": {"/tmp": "2Gi"},
}

PRIVILEGED_PRESET: dict[str, Any] = {
    "mem_limit": os.environ.get("AGENT_MEM_LIMIT", "2Gi"),
    "cpu_limit": os.environ.get("AGENT_CPU_LIMIT", "1"),
    "mem_request": "256Mi",
    "cpu_request": "100m",
    "allow_privilege_escalation": True,
    "cap_drop": [],
    "cap_add": [],
    "read_only": False,
    "host_network": False,
    "pids_limit": None,
    "tmpfs": None,
}


def get_k8s_presets() -> dict[str, dict[str, Any]]:
    """Return permissive, sandboxed, and privileged presets for UI and API."""
    return {
        "permissive": dict(PERMISSIVE_PRESET),
        "sandboxed": dict(SANDBOXED_PRESET),
        "privileged": dict(PRIVILEGED_PRESET),
    }


def _docker_mem_to_k8s(mem: str) -> str:
    """Convert Docker memory string to k8s quantity: '2g' -> '2Gi', '512m' -> '512Mi'."""
    if not mem:
        return mem
    lower = mem.lower()
    if lower.endswith("g") and not lower.endswith("gi"):
        return mem[:-1] + "Gi"
    if lower.endswith("m") and not lower.endswith("mi"):
        return mem[:-1] + "Mi"
    return mem


def _resolve_k8s_pod_config(cfg: K8sSecurityConfig) -> dict[str, Any]:
    """Build pod configuration dict from K8sSecurityConfig (preset + field overrides)."""
    level = (cfg.level or "permissive").lower()
    if level == "sandboxed":
        preset = SANDBOXED_PRESET
    elif level == "privileged":
        preset = PRIVILEGED_PRESET
    else:
        preset = PERMISSIVE_PRESET
    out: dict[str, Any] = dict(preset)
    if cfg.mem_limit is not None:
        out["mem_limit"] = _docker_mem_to_k8s(cfg.mem_limit)
    if cfg.cpu_quota is not None and cfg.cpu_period:
        # Convert Docker cpu_quota/cpu_period to k8s CPU limit string
        cores = cfg.cpu_quota / cfg.cpu_period
        out["cpu_limit"] = f"{int(cores * 1000)}m"
    if cfg.read_only is not None:
        out["read_only"] = cfg.read_only
    if cfg.network_mode == "host":
        out["host_network"] = True
    if cfg.pids_limit is not None:
        out["pids_limit"] = cfg.pids_limit
    return out


def _pod_name(agent_id: str) -> str:
    safe = "".join(c if c.isalnum() or c == "-" else "-" for c in agent_id.lower())
    return f"clawbot-agent-{safe}"[:63]


def _agent_k8s_security(storage: StorageBackend, base_path: str) -> K8sSecurityConfig:
    """Read agent's security config from .config/agent.json; fall back to defaults."""
    path = f"{AGENTS_DIR}/{base_path}/.config/agent.json"
    try:
        raw = json.loads(storage.read_sync(path).decode("utf-8"))
    except (FileNotFoundError, ValueError, TypeError, KeyError):
        return K8sSecurityConfig()
    k8s_raw = (raw.get("security") or {}).get("k8s")
    if not k8s_raw or not isinstance(k8s_raw, dict):
        return K8sSecurityConfig()
    try:
        return K8sSecurityConfig.model_validate(k8s_raw)
    except Exception:
        return K8sSecurityConfig()


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


def _software_bridge_env(agent_root: str) -> dict[str, str]:
    return {"AUTH_DIR": f"{agent_root}/data/whatsapp"}


def _software_port_mappings(installed_software: dict, registry) -> dict[str, int]:
    """Return hostPort mappings for software that exposes admin/HTTP APIs."""
    mappings: dict[str, int] = {}
    for slug in installed_software:
        catalog_entry = registry.get_entry(slug) or {}
        port = (catalog_entry.get("run") or {}).get("port")
        if port is None:
            continue
        try:
            base_port = int(port)
        except (TypeError, ValueError):
            continue
        if slug == "whatsapp-bridge":
            admin_port = base_port + 1
            mappings[f"{admin_port}"] = admin_port
    return mappings


def _build_k8s_client():
    """Create a Kubernetes CoreV1Api client.

    Priority:
      1. In-cluster config (when running inside k3s/k8s pod)
      2. KUBECONFIG env var
      3. /etc/rancher/k3s/k3s.yaml (k3s default)
      4. ~/.kube/config (standard kubeconfig)
    """
    try:
        from kubernetes import client, config  # noqa: PLC0415
    except ImportError as e:
        raise RuntimeError(
            "Kubernetes runtime requires the kubernetes package. "
            "Install with: pip install kubernetes>=31.0.0"
        ) from e

    try:
        config.load_incluster_config()
        logger.info("k8s client: using in-cluster config")
    except Exception:
        kubeconfig = os.environ.get("KUBECONFIG")
        if not kubeconfig and os.path.exists("/etc/rancher/k3s/k3s.yaml"):
            kubeconfig = "/etc/rancher/k3s/k3s.yaml"
        try:
            config.load_kube_config(config_file=kubeconfig)
            logger.info("k8s client: using kubeconfig %s", kubeconfig or "~/.kube/config")
        except Exception as exc:
            raise AgentRuntimeError(
                f"Cannot load k8s config: {exc}. "
                "Ensure k3s is running and kubeconfig is accessible at "
                "/etc/rancher/k3s/k3s.yaml or set KUBECONFIG env var."
            ) from exc

    api = client.CoreV1Api()
    try:
        api.list_namespace(limit=1)
    except Exception as exc:
        raise AgentRuntimeError(
            f"k8s API server not reachable: {exc}. Check k3s status: sudo systemctl status k3s"
        ) from exc

    logger.info("k8s client connected (namespace=%s)", K8S_NAMESPACE)
    return api


def _ensure_namespace(api) -> None:
    """Create the clawforce namespace if it doesn't exist."""
    from kubernetes import client  # noqa: PLC0415

    try:
        api.read_namespace(K8S_NAMESPACE)
    except Exception:
        ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=K8S_NAMESPACE))
        try:
            api.create_namespace(ns)
            logger.info("Created namespace: %s", K8S_NAMESPACE)
        except Exception as e:
            logger.warning("Could not create namespace %s: %s", K8S_NAMESPACE, e)


def _detect_host_mount_source(api, container_path: str) -> str | None:
    """Auto-detect the host source path for a mount destination in the current pod."""
    pod_name = socket_mod.gethostname()
    if not pod_name:
        return None
    try:
        pod = api.read_namespaced_pod(pod_name, K8S_NAMESPACE)
        # Build volume name -> host_path map
        vol_map: dict[str, str] = {}
        for volume in pod.spec.volumes or []:
            if volume.host_path:
                vol_map[volume.name] = volume.host_path.path
        # Find which volume mount matches container_path
        for container in pod.spec.containers or []:
            for vm in container.volume_mounts or []:
                if vm.mount_path == container_path and vm.name in vol_map:
                    host_path = vol_map[vm.name]
                    logger.info("Auto-detected host mount: %s -> %s", container_path, host_path)
                    return host_path
    except Exception as exc:
        logger.debug("Could not auto-detect k8s host mount: %s", exc)
    return None


def _build_agent_pod(  # noqa: PLR0913
    pod_name: str,
    env: dict[str, str],
    agent_path_host: str,
    pod_cfg: dict[str, Any],
    image: str,
    namespace: str,
    port_mappings: dict[str, int],
) -> Any:
    """Build a V1Pod spec for an agent worker."""
    from kubernetes.client import (  # noqa: PLC0415
        V1Capabilities,
        V1Container,
        V1ContainerPort,
        V1EmptyDirVolumeSource,
        V1EnvVar,
        V1HostPathVolumeSource,
        V1ObjectMeta,
        V1Pod,
        V1PodSpec,
        V1ResourceRequirements,
        V1SecurityContext,
        V1Volume,
        V1VolumeMount,
    )

    k8s_env = [V1EnvVar(name=k, value=str(v)) for k, v in env.items()]

    cap_add = pod_cfg.get("cap_add") or []
    cap_drop = pod_cfg.get("cap_drop") or []
    capabilities = None
    if cap_add or cap_drop:
        capabilities = V1Capabilities(
            add=cap_add or None,
            drop=cap_drop or None,
        )

    sec_ctx = V1SecurityContext(
        allow_privilege_escalation=pod_cfg.get("allow_privilege_escalation", False),
        capabilities=capabilities,
        read_only_root_filesystem=pod_cfg.get("read_only", False),
    )

    resources = V1ResourceRequirements(
        limits={
            "memory": pod_cfg.get("mem_limit", "2Gi"),
            "cpu": pod_cfg.get("cpu_limit", "1"),
        },
        requests={
            "memory": pod_cfg.get("mem_request", "256Mi"),
            "cpu": pod_cfg.get("cpu_request", "100m"),
        },
    )

    volumes = [
        V1Volume(
            name="agent-data",
            host_path=V1HostPathVolumeSource(path=str(agent_path_host), type="DirectoryOrCreate"),
        )
    ]
    volume_mounts = [V1VolumeMount(name="agent-data", mount_path="/agent")]

    if pod_cfg.get("tmpfs"):
        for mount_path, size in pod_cfg["tmpfs"].items():
            vol_name = "tmpfs" + mount_path.replace("/", "-")
            volumes.append(
                V1Volume(
                    name=vol_name,
                    empty_dir=V1EmptyDirVolumeSource(medium="Memory", size_limit=size),
                )
            )
            volume_mounts.append(V1VolumeMount(name=vol_name, mount_path=mount_path))

    container_ports = [
        V1ContainerPort(container_port=p, host_port=p, protocol="TCP")
        for p in port_mappings.values()
    ]

    container = V1Container(
        name="agent",
        image=image,
        image_pull_policy=K8S_IMAGE_PULL_POLICY,
        command=["python", "-m", "clawbot.worker.app"],
        env=k8s_env,
        volume_mounts=volume_mounts,
        working_dir="/agent/workspace",
        security_context=sec_ctx,
        resources=resources,
        ports=container_ports or None,
    )

    return V1Pod(
        metadata=V1ObjectMeta(
            name=pod_name,
            namespace=namespace,
            labels={"app": "clawbot-agent", "clawforce-agent-id": pod_name[:63]},
        ),
        spec=V1PodSpec(
            restart_policy="Never",
            host_network=pod_cfg.get("host_network", False),
            containers=[container],
            volumes=volumes,
        ),
    )


class K8sRuntime(WorkerRuntimeBase):
    """Run one agent per Kubernetes Pod (k3s or any k8s cluster)."""

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
        self._api = None

    def _client(self):
        if self._api is None:
            self._api = _build_k8s_client()
            _ensure_namespace(self._api)
        return self._api

    def get_security_presets(self) -> dict[str, dict[str, Any]]:
        """Return k8s security presets for API/UI."""
        return get_k8s_presets()

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
            name = _pod_name(agent_id)
            base_path = agent.base_path or agent_id
            k8s_cfg = _agent_k8s_security(self._storage, base_path)
            pod_cfg = _resolve_k8s_pod_config(k8s_cfg)

            cp = control_plane_overrides(agent)
            admin_url: str = cp["admin_url"]

            # Replace localhost/127.0.0.1 with k8s service DNS so agents can reach admin
            _uses_local = (
                "localhost" in admin_url
                or "127.0.0.1" in admin_url
                or "host.docker.internal" in admin_url
            )
            if _uses_local:
                admin_url = K8S_ADMIN_SERVICE_URL
                logger.info("Using k8s service URL for admin: %s", admin_url)

            storage_root = str(
                getattr(self._storage, "root", None)
                or os.environ.get("ADMIN_STORAGE_ROOT", "/data")
            )
            agent_host_base = os.environ.get("AGENT_STORAGE_HOST_PATH")
            if not agent_host_base:
                agent_host_base = (
                    _detect_host_mount_source(self._client(), storage_root) or storage_root
                )
            logger.info("Agent host base: %s (storage_root=%s)", agent_host_base, storage_root)

            agent_root_in_pod = "/agent"
            agent_config_store = AgentConfigStore(get_database(), fernet=get_fernet())
            agent_config = agent_config_store.get_config(agent_id) or {}
            installed_software = (agent_config.get("tools") or {}).get("software") or {}
            registry = get_software_registry()
            extra_ports = _software_port_env(installed_software, registry)
            port_mappings = _software_port_mappings(installed_software, registry)
            bridge_env = _software_bridge_env(agent_root_in_pod)

            env = {
                "AGENT_ID": agent_id,
                "AGENT_ROOT": agent_root_in_pod,
                "ADMIN_URL": admin_url,
                "AGENT_TOKEN": cp["agent_token"],
                **extra_ports,
                **bridge_env,
                "AGENT_LOG_LEVEL": k8s_cfg.log_level or os.environ.get("AGENT_LOG_LEVEL", "INFO"),
                "PYTHONUNBUFFERED": "1",
            }

            variables_store = AgentVariablesStore(get_database())
            variables = variables_store.get_variables(agent_id)
            for key, value in variables.items():
                if key and value:
                    env[key] = str(value)

            agent_path_host = (Path(agent_host_base) / AGENTS_DIR / base_path).resolve()

            def _run():
                api = self._client()
                # Remove stale pod if it exists
                try:
                    api.delete_namespaced_pod(name, K8S_NAMESPACE, grace_period_seconds=0)
                    logger.debug("Removed stale pod: %s", name)
                except Exception:
                    pass

                agent_path_host.mkdir(parents=True, exist_ok=True)

                pod_spec = _build_agent_pod(
                    pod_name=name,
                    env=env,
                    agent_path_host=str(agent_path_host),
                    pod_cfg=pod_cfg,
                    image=K8S_IMAGE,
                    namespace=K8S_NAMESPACE,
                    port_mappings=port_mappings,
                )
                pod = api.create_namespaced_pod(K8S_NAMESPACE, pod_spec)
                logger.info("Created pod %s in namespace %s", name, K8S_NAMESPACE)
                return pod

            loop = asyncio.get_running_loop()
            pod = await loop.run_in_executor(None, _run)
            self._running[agent_id] = {"pod_name": name, "pod": pod}
            self._store.update_agent(agent_id, status="connecting")
            await asyncio.sleep(1.0)
        except AgentRuntimeError:
            self._store.update_agent(agent_id, status="stopped")
            raise
        except Exception as exc:
            self._store.update_agent(agent_id, status="stopped")
            logger.exception("Failed to start agent %s", agent_id)
            raise AgentRuntimeError(f"Failed to start agent: {exc!s}") from exc

    async def _cleanup_entry(self, agent_id: str) -> None:
        """Remove a dead pod entry from _running."""
        entry = self._running.pop(agent_id, None)
        if not entry:
            return
        pod_name = entry.get("pod_name")
        if pod_name:

            def _remove():
                try:
                    self._client().delete_namespaced_pod(
                        pod_name, K8S_NAMESPACE, grace_period_seconds=0
                    )
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
        pod_name = entry["pod_name"]

        def _stop():
            try:
                self._client().delete_namespaced_pod(
                    pod_name, K8S_NAMESPACE, grace_period_seconds=5
                )
            except Exception:
                pass

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _stop)
        self._store.update_agent(agent_id, status="stopped")

    async def _is_worker_alive(self, agent_id: str) -> bool:
        entry = self._running.get(agent_id, {})
        pod_name = entry.get("pod_name")
        if not pod_name:
            return False

        def _check():
            try:
                pod = self._client().read_namespaced_pod(pod_name, K8S_NAMESPACE)
                phase = (pod.status or {}).phase if pod.status else None
                return phase == "Running"
            except Exception:
                return False

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _check)

    def _storage_prefix(self, agent_id: str) -> str:
        agent = self._store.get_agent(agent_id)
        base_path = (agent.base_path or agent_id) if agent else agent_id
        return f"{AGENTS_DIR}/{base_path}"

    async def _is_pod_running(self, agent_id: str) -> bool:
        """True if agent pod exists and is running (may repopulate _running)."""
        if agent_id in self._running:
            return await self._is_worker_alive(agent_id)
        name = _pod_name(agent_id)

        def _check():
            try:
                pod = self._client().read_namespaced_pod(name, K8S_NAMESPACE)
                phase = pod.status.phase if pod.status else None
                return pod if phase == "Running" else None
            except Exception:
                return None

        loop = asyncio.get_running_loop()
        try:
            pod = await asyncio.wait_for(loop.run_in_executor(None, _check), timeout=5.0)
            if pod:
                self._running[agent_id] = {"pod_name": name, "pod": pod}
                return True
        except asyncio.TimeoutError:
            logger.debug("k8s pod status check timed out for %s", name)
        return False

    async def _list_from_storage(self, agent_id: str, root: str) -> list[str]:
        prefix = f"{self._storage_prefix(agent_id)}/{root}"
        try:
            return await self._storage.list_dir(prefix)
        except Exception:
            return []

    async def _read_from_storage(self, agent_id: str, root: str, path: str) -> str | None:
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
        if await self._is_pod_running(agent_id):
            logger.debug("Agent %s not connected; using storage fallback", agent_id)
            return await self._list_from_storage(agent_id, "workspace")
        raise AgentRuntimeError(f"Agent {agent_id} is not connected")

    async def list_profile(self, agent_id: str) -> list[str]:
        if self._is_ws_connected(agent_id):
            return await super().list_profile(agent_id)
        if await self._is_pod_running(agent_id):
            return await self._list_from_storage(agent_id, "profiles")
        raise AgentRuntimeError(f"Agent {agent_id} is not connected")

    async def read_workspace_file(self, agent_id: str, path: str) -> str | None:
        if self._is_ws_connected(agent_id):
            return await super().read_workspace_file(agent_id, path)
        if await self._is_pod_running(agent_id):
            return await self._read_from_storage(agent_id, "workspace", path)
        raise AgentRuntimeError(f"Agent {agent_id} is not connected")

    async def read_profile_file(self, agent_id: str, path: str) -> str | None:
        if self._is_ws_connected(agent_id):
            return await super().read_profile_file(agent_id, path)
        if await self._is_pod_running(agent_id):
            return await self._read_from_storage(agent_id, "profiles", path)
        raise AgentRuntimeError(f"Agent {agent_id} is not connected")

    def supports_terminal(self) -> bool:
        return True

    def get_terminal_target(self, agent_id: str) -> tuple[str, Any] | None:
        if agent_id in self._running:
            return ("k8s", self._running[agent_id]["pod_name"])
        name = _pod_name(agent_id)
        try:
            pod = self._client().read_namespaced_pod(name, K8S_NAMESPACE)
            if pod.status and pod.status.phase == "Running":
                self._running[agent_id] = {"pod_name": name, "pod": pod}
                return ("k8s", name)
        except Exception:
            pass
        return None

    def get_container_logs(self, agent_id: str, tail: int = 200) -> str:
        """Return the last *tail* lines of the pod logs."""
        pod_name = _pod_name(agent_id)
        try:
            return self._client().read_namespaced_pod_log(
                pod_name,
                K8S_NAMESPACE,
                tail_lines=tail,
                container="agent",
            )
        except Exception as exc:
            return f"Pod {pod_name!r} logs not available: {exc}\n"

    def stream_container_logs(self, agent_id: str, tail: int = 100):
        """Generator that yields log lines from the pod."""
        pod_name = _pod_name(agent_id)
        try:
            log_stream = self._client().read_namespaced_pod_log(
                pod_name,
                K8S_NAMESPACE,
                tail_lines=tail,
                follow=True,
                container="agent",
                _preload_content=False,
            )
            for line in log_stream:
                if isinstance(line, bytes):
                    yield line.decode("utf-8", errors="replace").rstrip("\n")
                else:
                    yield str(line).rstrip("\n")
        except Exception:
            return


async def bridge_k8s_terminal(websocket: WebSocket, pod_name: str, agent_id: str) -> None:
    """Bridge WebSocket <-> kubectl exec (interactive shell in agent pod)."""
    try:
        from kubernetes.stream import stream as k8s_stream  # noqa: PLC0415
    except ImportError:
        await websocket.send_json({"type": "error", "data": "kubernetes SDK not installed"})
        return

    try:
        api = _build_k8s_client()
    except Exception as e:
        await websocket.send_json({"type": "error", "data": f"k8s client error: {e}"})
        return

    loop = asyncio.get_running_loop()
    closed = asyncio.Event()

    def _create_exec_stream():
        return k8s_stream(
            api.connect_get_namespaced_pod_exec,
            pod_name,
            K8S_NAMESPACE,
            command=["/bin/bash", "-i"],
            container="agent",
            stdin=True,
            stdout=True,
            stderr=True,
            tty=True,
            _preload_content=False,
        )

    try:
        ws_client = await loop.run_in_executor(None, _create_exec_stream)
    except Exception as e:
        logger.exception("k8s exec failed for agent %s", agent_id)
        await websocket.send_json({"type": "error", "data": str(e)})
        return

    async def read_pod_and_forward() -> None:
        try:
            while not closed.is_set():

                def _read():
                    if not ws_client.is_open():
                        return None
                    ws_client.update(timeout=0.1)
                    data = ""
                    if ws_client.peek_stdout():
                        data += ws_client.read_stdout()
                    if ws_client.peek_stderr():
                        data += ws_client.read_stderr()
                    return data

                data = await loop.run_in_executor(None, _read)
                if data is None:
                    break
                if data:
                    try:
                        await websocket.send_json({"type": "output", "data": data})
                    except Exception:
                        break
                else:
                    await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass
        finally:
            closed.set()

    async def forward_websocket_to_pod() -> None:
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
                        await loop.run_in_executor(None, ws_client.write_stdin, data)
                elif msg_type == "resize":
                    cols = msg.get("cols", 80)
                    rows = msg.get("rows", 24)
                    try:
                        resize_msg = json.dumps({"Width": cols, "Height": rows})
                        await loop.run_in_executor(None, ws_client.write_channel, 4, resize_msg)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass
        finally:
            closed.set()

    try:
        read_task = asyncio.create_task(read_pod_and_forward())
        write_task = asyncio.create_task(forward_websocket_to_pod())
        await asyncio.gather(read_task, write_task)
    finally:
        closed.set()
        try:
            ws_client.close()
        except Exception:
            pass
