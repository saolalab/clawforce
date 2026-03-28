# Clawforce

<div align="center">

<img src="clawforce-ui/src/assets/clawforce.png" alt="Clawforce" width="160" />

**Your AI agent team. One click away.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/saolalab/clawforce/actions/workflows/ci.yml/badge.svg)](https://github.com/saolalab/clawforce/actions/workflows/ci.yml)

</div>

---

> **Deploy autonomous AI teams that run your work — 24/7, securely, at scale.**
>
> Clawforce is the infrastructure for deploying **persistent, proactive agent workforces** that execute complex workflows, collaborate as teams, and deliver real outcomes — without constant human supervision.

<p align="center">
  <a href="https://www.loom.com/share/ec254662421346cba0c9827cc6cf3e0c">
    <img src="docs/public/demo-thumbnail.gif" alt="Demo Video" width="720">
  </a>
  <br>
  <em>Click to play</em>
</p>

---

## 🏢 Agent Infrastructure for Work

**Orchestrate AI workforces** across your organization.

### ⚡ 1-Click Deployment

Deploy from idea to production in seconds — no code required.

- **Marketplace & Templates** — Pre-built agents for code review, security, support, analysis; customize as needed
- **Visual Portal** — Deploy, configure, and monitor via dashboard
- **Auto-Configuration** — Tools, permissions, and integrations set by agent role

### 🤖 24/7 Background Companions

Built on Clawbot functionalities; adds workspace management and team collaboration.

- **Persistent** — Agents maintain state, remember context, and keep working across sessions
- **Proactive** — Schedule via cron, trigger on events, or let agents monitor and act autonomously
- **Collaborative** — A2A protocols, task delegation, shared Kanban boards
- **Agent Workspaces** — Dedicated workspace per agent for files and artifacts.


### 🔒 Security

Isolation at every layer:

- **Containers** — Three modes: **permissive** (default; `CAP_DROP=ALL`, resource limits), **sandboxed** (read-only, no network, strictest), **privileged** (full access for compatibility)
- **Sandboxing** — Workspace-only access; no visibility into other agents or system files
- **Secrets** — Encrypted vault, runtime injection, never on disk
- **Network** — SSRF protection, private IP blocking, per-agent isolation
- **Shell** — Dangerous operators blocked by default; optional relaxed mode; execution restricted to workspace
- **Approval & Audit** — Optional admin approval for tools; full activity logging

---

## What You Can Build

| Use Case | Agent Setup |
|----------|-------------|
| **DevOps Automation** | Agents that monitor deployments, respond to incidents, and fix common issues autonomously |
| **Security Operations** | Continuous vulnerability scanning, compliance checking, and threat response |
| **Customer Support** | Multi-channel agents that handle tickets, escalate intelligently, and learn from resolutions |
| **Content Pipeline** | Agents that research, draft, review, and publish — with human approval gates |
| **Data Operations** | ETL pipelines, report generation, and anomaly detection running 24/7 |
| **Code Review** | Persistent reviewers that understand your codebase and enforce standards |

---

## 📋 Product Principles

- **Easy-to-Use Agent Team Setup** — Our focus. Deploy from marketplace in 1 click; role-based templates, visual portal, minimal friction.
- **Background Agents, No GUI Automation** — We do not support Computer Use or Browser Use. Use **MCP** (Model Context Protocol) instead.
- **Best Practices** — Security first; use trusted software; internal MaaS (MCP-as-a-Service); internal MCP & Skills Registry; approval gates for sensitive tools.

See [Product Principles & Best Practices](https://saolalab.github.io/clawforce/guide/principles) in the docs.


## How It Works

### The Platform

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Dashboard                                                                   │
│  Agent Marketplace · 1-Click Deploy · Plan Boards · Workspace Explorer       │
│  Live Activity Logs · Interactive Terminals · Organization Management        │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ HTTP / WebSocket
┌───────────────────────────────┴──────────────────────────────────────────────┐
│  Admin Control Plane                                                         │
│  REST API · WebSocket Hub · Agent Runtimes · Vault Secrets · Plan Store      │
│  Auth & RBAC · Workspace Service · Scheduler · Settings                      │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ Isolated WebSocket (per-agent)
┌───────────────────────────────┴──────────────────────────────────────────────┐
│  Agent Workers (isolated containers)                                         │
│  LLM Core Loop · Shell & Filesystem · Web Access · MCP Tools · A2A Protocol  │
│  Channel Adapters · Cron Scheduler · Skills · Plans · Spawning               │
└──────────────────────────────────────────────────────────────────────────────┘
```

Each agent worker runs in a **fully isolated container** (Docker or Podman) with its own filesystem, network stack, and resource limits. The control plane multiplexes all communication through a single WebSocket hub — no HTTP ports exposed per agent.

### Agent Lifecycle

1. **Deploy**: Click to deploy from marketplace, or create custom agent from template
2. **Configure**: Set objectives, tools, permissions, and integrations through portal
3. **Run**: Agent starts in isolated container, connects to control plane
4. **Execute**: Agent works autonomously — executes tasks, coordinates with team, delivers artifacts
5. **Monitor**: Real-time logs, workspace browsing, and interactive terminal access
6. **Scale**: Spin up more agents as workload grows

---

## Quick Start

### One-Line Install (Recommended)

The fastest way to get started — installs Docker (if needed) and runs Clawforce.
Works with both **Docker** (default) and **Podman**.

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash
```

**With Podman:**
```bash
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --engine podman
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 | iex

# Or with Podman:
.\install.ps1 -Engine podman
```

> **Note:** Administrator privileges are only required if Docker Desktop or Podman is not yet installed (the script will install it via `winget`). If either is already installed, a regular PowerShell session works fine.

After installation, open **http://localhost:8080** and log in with `admin`/`admin`.

> **Security:** Change the default password immediately after first login, or pass `--admin-pass <yourpassword>` to the installer.

**You're ready to deploy your first agent from the marketplace.**

---

### Install Options

```bash
# Custom port and admin password
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --port 9000 --admin-pass mypassword

# Custom port and admin password (Podman)
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --engine podman --port 9000 --admin-pass mypassword

# Use process runtime instead of container isolation
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --process-runtime

# Uninstall (Docker)
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --uninstall

# Uninstall (Podman)
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --engine podman --uninstall
```

**Windows:**
```powershell
# Uninstall (Docker)
.\install.ps1 -Uninstall

# Uninstall (Podman)
.\install.ps1 -Engine podman -Uninstall
```

### Run with Docker or Podman

Maximum security — each agent runs in its own isolated container:

**Docker:**
```bash
docker run -d -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $HOME/.clawforce-data:/data \
  -e AGENT_STORAGE_HOST_PATH=$HOME/.clawforce-data \
  ghcr.io/saolalab/clawforce:latest
```

**Podman:**

> **Linux prerequisite:** Enable the Podman socket before running:
> ```bash
> systemctl --user start podman.socket
> systemctl --user enable podman.socket  # persist across reboots
> ```

```bash
podman run -d -p 8080:8080 \
  -v $XDG_RUNTIME_DIR/podman/podman.sock:/var/run/docker.sock \
  -v $HOME/.clawforce-data:/data \
  -e AGENT_STORAGE_HOST_PATH=$HOME/.clawforce-data \
  -e CONTAINER_ENGINE=podman \
  ghcr.io/saolalab/clawforce:latest
```

### Native Install

```bash
pip install git+https://github.com/saolalab/clawforce.git
clawforce setup
clawforce serve
```

---

## Features at a Glance

| Category | Capabilities |
|----------|--------------|
| **Agent Management** | Create, configure, start/stop, monitor, and scale agents from dashboard |
| **Marketplace** | Pre-built agent templates for common workflows — deploy in 1 click |
| **Team Coordination** | A2A discovery, direct messaging, shared Kanban plans, task delegation |
| **Security** | Container isolation (Docker/Podman), vault secrets, network controls, shell policies, RBAC |
| **Tools** | Shell, filesystem, web search, MCP servers, custom integrations |
| **Channels** | Slack, Discord, Telegram, WhatsApp, Email, Feishu |
| **Scheduling** | Cron-based triggers, event-driven execution, persistent background work |
| **Observability** | Live logs, workspace explorer, interactive terminals, plan boards |

---

## Terminology

- **Control Plane** (`clawforce`): The API server, scheduler, and orchestration hub
- **Agent**: A logical workload specification — role, objectives, tools, permissions
- **Worker** (`clawbot`): The runtime that executes one agent instance in isolation
- **Plan**: Orchestrator for agent work — shared Kanban board, tasks, artifacts. Coordinator decides when each agent engages; activation marks plan ready. Agents pull from external systems (GitHub, Jira) and create tasks; Plan does not sync. See [Plans guide](https://saolalab.github.io/clawforce/guide/plans).
- **Workspace**: Isolated filesystem directory where an agent reads, writes, and builds

---

## Development

```bash
git clone https://github.com/saolalab/clawforce.git
cd clawforce
make install && make setup
make backend   # Terminal 1: API at http://localhost:8080
make frontend  # Terminal 2: Vite at http://localhost:5173
```

Build from source:

**Docker:**
```bash
docker build -t clawforce:latest -f deploy/Dockerfile .
docker run -d -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $HOME/.clawforce-data:/data \
  -e AGENT_STORAGE_HOST_PATH=$HOME/.clawforce-data \
  -e AGENT_IMAGE=clawforce:latest \
  clawforce:latest
```

**Podman:**
```bash
podman build -t clawforce:latest -f deploy/Dockerfile .
podman run -d -p 8080:8080 \
  -v $XDG_RUNTIME_DIR/podman/podman.sock:/var/run/docker.sock \
  -v $HOME/.clawforce-data:/data \
  -e AGENT_STORAGE_HOST_PATH=$HOME/.clawforce-data \
  -e AGENT_IMAGE=clawforce:latest \
  -e CONTAINER_ENGINE=podman \
  clawforce:latest
```

Or using the Makefile (auto-detects engine, override with `ENGINE=podman`):
```bash
make container             # build + run
make container-logs        # tail logs
ENGINE=podman make container  # use podman
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

---

## Roadmap

| Area | Planned |
|------|---------|
| **Enterprise** | SSO/SAML, LDAP, compliance reporting, SLA guarantees |
| **IAM** | Fine-grained RBAC, service accounts, API keys, OIDC federation |
| **Multi-Backend** | Kubernetes, AWS ECS, GCP Cloud Run, Azure Container Instances |
| **High Availability** | Multi-node control plane, agent failover, distributed scheduler |
| **Observability** | Prometheus metrics, Grafana dashboards, OpenTelemetry tracing |
| **Marketplace** | Community plugins, third-party integrations, private registries |
| **Cost & Quotas** | Resource quotas per org, usage tracking, budget alerts |

---

## Support

[![Buy Me A Coffee](https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&slug=hungtd9&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff)](https://www.buymeacoffee.com/hungtd9)

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
