# Terminology

This document defines product terms so that design and documentation stay consistent across the control plane and worker runtime.

## Term mapping

| Product term | Definition |
|--------------|------------|
| **Control plane** | clawforce: REST API, WebSocket hub, auth, vault, agent pools, plan store. Where operators and the UI talk to the system. |
| **Agent** | Logical unit: identity (id, name, team), config (model, tools, channels), and desired state. Stored as `AgentDef`; data under `agents/{agent_id}/`. |
| **Agent instance / worker** | One running process or container executing one agent. Implemented by clawbot; one WebSocket connection per instance to the control plane. |
| **Agent pool** | Runtime backend that starts/stops and talks to agent instances: `process` (subprocess), `docker` (container), or future backends. |
| **Worker** (clawbot) | The clawbot process that runs a single agent. `WorkerContext` holds everything that instance needs (config, loop, channels). |
| **Start / stop agent** | Start = run one instance for that agent. Stop = terminate the instance (scale to 0). |
| **Agent status** | Workload state of the agent instance: see [Status values](#status-values) below. |
| **Workspace** | Per-agent filesystem: profiles (read-only), workspace (read/write), .config, .sessions. Isolated per agent. |
| **Team** | Grouping of agents (e.g. for start/stop as a set). Organizational. |
| **Plan** | Orchestrator for agent work. A local Kanban board with tasks, artifacts, and agent assignments. The coordinator (plan creator) decides when each agent engages; activation marks the plan ready but does not require all agents to be running. Plan does not sync with external systems; agents handle that. |
| **Session** | One conversation thread (e.g. channel + chat_id). Stored as JSONL; append-only for LLM context. |
| **Secrets / Vault** | Credentials (API keys, tokens) injected at runtime; not stored in agent-accessible config or workspace. |

## Status values

Agent instance status follows a small lifecycle:

| Status | Meaning |
|--------|---------|
| **stopped** | No instance running (intentionally or not yet started). |
| **running** | Instance is up and (when applicable) connected to the control plane. |
| **failed** | Instance exited or unhealthy. |

Plan status is separate: `draft` → `active` → `paused` | `completed`.

## Plan vs external systems

External systems (GitHub Projects, Jira) remain the source of truth for their data. Plan is the orchestrator where the coordinator and agents record and orchestrate work. Agents perform any sync; Plan stores the coordination view. The coordinator decides when each agent starts working; not all agents need to be active at once.

## Naming conventions in code and config

- **`agent_id`** — Unique id for the agent (logical unit and its data path).
- **`agent_root`** — Root directory for that agent's data (e.g. `agents/{agent_id}/`).
- **`AGENT_*`** env vars — Configuration for the **worker** (image, resource limits, host path for bind mounts). See [Configuration](/guide/configuration).
- **`ADMIN_*`** env vars — Configuration for the **control plane** (storage, auth, pool backend, public URL).

## See also

- [Quick Start](/guide/quickstart) — Installation and first steps
- [Plans](/guide/plans) — Orchestrator for agent work
- [Configuration](/guide/configuration) — Environment variables and settings
