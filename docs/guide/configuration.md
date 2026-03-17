# Configuration Reference

Environment variables and configuration for Clawforce (admin control plane). For terminology (control plane, agent, worker, pool), see [Terminology](/reference/terminology).

## Naming convention

- **`ADMIN_`** — Config for the control plane (clawforce): storage, auth, pool backend, public URL, etc.
- **`AGENT_`** — Config for the agent instance runtime (clawbot worker): image, host path for bind mounts, Docker resource limits, etc.

## Quick Start Defaults (Docker image)

These are pre-set in the published Docker image for a minimal startup command:

| Variable | Default | Notes |
|----------|---------|-------|
| `ADMIN_SETUP_USERNAME` | `admin` | Override in production |
| `ADMIN_SETUP_PASSWORD` | `admin` | Override in production |
| `AGENT_IMAGE` | `ghcr.io/saolalab/clawforce:latest` | Worker container image |
| `ADMIN_RUNTIME_BACKEND` | `docker` | Use `process` for subprocess runtime |
| `ADMIN_PUBLIC_URL` | `http://host.docker.internal:8080` | Worker→admin connectivity. **Critical for Docker runtime.** See [Troubleshooting](#troubleshooting-503-agent-offline) if workspace returns 503. |

## Security-Related

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_JWT_SECRET` | Secret key for signing JWT access tokens. **Required in production.** | Ephemeral (dev only) |
| `CLAWFORCE_ENV` | Set to `production` to require `ADMIN_JWT_SECRET` and disable ephemeral JWT. | `development` |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins (no spaces). | `http://localhost:5173,http://localhost:8080` |

## Docker Pool

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_IMAGE` | Worker image name (same clawforce image). | `ghcr.io/saolalab/clawforce:latest` |
| `AGENT_STORAGE_HOST_PATH` | Host-side base path for agent bind mounts. Override when the control plane runs in Docker so worker containers get the correct host path for `agents/{id}`. | `ADMIN_STORAGE_ROOT` |
| `AGENT_DOCKER_MEM_LIMIT` | Memory limit per agent container (e.g. `2g`). Fallback when agent config has no override. | `2g` |
| `AGENT_DOCKER_CPU_QUOTA` | CPU quota (CFS) per agent container. Fallback when agent config has no override. | `100000` |
| `AGENT_DOCKER_CPU_PERIOD` | CPU period (CFS) in microseconds per agent container. Fallback when agent config has no override. | `100000` |

### Agent config: `security.docker`

Per-agent Docker security level (applied when starting the container). Set via admin API or in agent config.

| Key | Description | Default |
|-----|-------------|---------|
| `level` | Preset: `permissive` (Standard: network access, catalog software install), `sandboxed` (Safe: read-only rootfs, no network), or `privileged` (Power: full system access, sudo/apt-get). | `permissive` |
| `readOnly` | Override read-only rootfs (default from preset). | (from preset) |
| `networkMode` | Override network mode (e.g. `none`, `bridge`). | (from preset) |
| `pidsLimit` | Override PID limit; 0 = unlimited. | (from preset) |
| `mem_limit` | Override memory limit (e.g. `2g`). | (from preset) |
| `cpu_quota` / `cpu_period` | Override CPU limits. | (from preset) |

### Agent config: `tools.approval`

Per-tool execution policy: run immediately or ask the user in-channel before running.

| Key | Description | Default |
|-----|-------------|---------|
| `default_mode` | `always_run` or `ask_before_run`. | `always_run` |
| `per_tool` | Map of tool name → mode, e.g. `{"exec": "ask_before_run", "write_file": "ask_before_run"}`. | `{}` |
| `timeout_seconds` | Seconds to wait for user reply; then auto-deny. | `120` |

## Storage

Under `ADMIN_STORAGE_ROOT`: `admin/` (admin DB and `project_data/`) and `agents/{agent_id}/` (per-agent data). Workers only ever see their own `agents/{id}` directory.

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_STORAGE_ROOT` | Root directory; contains `admin/` and `agents/`. | (app-dependent) |
| `AGENT_STORAGE_HOST_PATH` | Host-side base path for agent worker bind mounts. Defaults to `ADMIN_STORAGE_ROOT`, which works for native installs. Override when the control plane runs in Docker (e.g. `-v /host/data:/data` → `AGENT_STORAGE_HOST_PATH=/host/data`). | `ADMIN_STORAGE_ROOT` |
| `ADMIN_STORAGE_BACKEND` | Backend: `local` or `s3`. | `local` |

## User Management (CLI)

Admin users are managed via the CLI. Use `--data-dir` to specify the data directory (default: `./data`).

| Command | Description |
|---------|-------------|
| `clawforce user create <username>` | Create a new user. Use `--password` / `-p` or prompt; `--role` (default: admin). |
| `clawforce user update <username>` | Update user. Use `--password` and/or `--role`. Prompts for password if neither given. |
| `clawforce user list` | List all users. |
| `clawforce user set-password <username>` | Reset password (interactive). |
| `clawforce user reset <username>` | Reset password (alias for set-password). |

Examples:

```bash
clawforce user create alice --password secret
clawforce user create bob --password secret --role admin
clawforce user update alice --role admin
clawforce user reset alice
```

## Troubleshooting: 503 Agent Offline

When opening an agent in the browser, workspace/profile endpoints may return **503 Service Unavailable** with "Agent is not connected". This means the agent worker has not established a WebSocket connection to the admin.

**Docker mode:** The agent container must reach `ADMIN_PUBLIC_URL` to connect.

**Cross-platform support (Mac, Windows, Linux):** The default `http://host.docker.internal:8080` works on all platforms. The runtime automatically adds `extra_hosts: host.docker.internal=host-gateway` to agent containers (Docker 20.10+ on Linux). If `ADMIN_PUBLIC_URL` is `localhost` or `127.0.0.1`, it is auto-converted to `host.docker.internal` so agents can reach the admin.

**Other cases:**

1. **Admin behind reverse proxy:** Ensure WebSocket upgrade is configured (e.g. nginx `proxy_http_version 1.1`, `proxy_set_header Upgrade`, `Connection`). Use the public URL (e.g. `https://admin.example.com`) so the agent can connect.

2. **Remote Docker daemon:** `DOCKER_HOST` points to a remote host. Set `ADMIN_PUBLIC_URL` to an IP/hostname reachable from that host (e.g. the host's public IP).

3. **Check agent logs:** `docker logs <container_name>` to see if the worker fails to connect (e.g. connection refused, timeout).

4. **Multiple workers (`--workers > 1`):** Each worker has its own WebSocket connections and activity registry. If the agent connects to worker A but the Activity tab hits worker B, you'll see "Agent is running but activity may be on another server process." Configure **sticky sessions** so `/api/control/ws` and `/api/agents/*/logs` route to the same worker (e.g. nginx `ip_hash` or `hash $remote_addr`).

## Troubleshooting: Docker Disk Space

**Symptom:** Software installation fails with "Install software failed" or "Unknown error" when installing npm/pip packages from the marketplace.

**Cause:** Docker Desktop uses a virtual disk (default ~64 GB). Images, containers, and agent installs (npm, pip) all consume this space. When full, installs fail with ENOSPC or the agent container may be killed.

**Fix:**

1. **Increase Docker disk size:** Docker Desktop → Settings → Resources → Advanced → **Disk image size** (increase to 80–120 GB or more). Click **Apply & Restart**.

2. **Free space:** Run `docker system prune -a` to remove unused images and containers. Optionally `docker system prune -a --volumes` to also remove volumes (this will wipe agent data).

3. **Check usage:** `docker system df -v` shows disk usage by images, containers, and volumes.

4. **Sandboxed mode:** If using sandboxed Docker mode, `/tmp` is limited to 2 GB. Use permissive mode for very large npm installs.

## Audit Logging

Security events are emitted by the `clawforce.audit` logger. Configure your logging (e.g. in `logging.yaml` or via `LOG_*` if supported) to capture this logger and send it to your SIEM or log aggregation.

Events:

- **auth_event**: `event`, `user_id`, `ip`, `success`, `detail`, `timestamp`
- **vault_access**: `agent_id`, `ip`, `success`, `detail`, `timestamp`
