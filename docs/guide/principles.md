# Product Principles & Best Practices

Clawforce is designed for **easy-to-use agent team setup** and **background automation**. This guide outlines product philosophy and recommended practices.

---

## Our Focus: Easy Agent Team Setup

Clawforce prioritizes:

- **1-Click Deployment** — Deploy pre-built agents from the marketplace; no code required
- **Visual Configuration** — Set objectives, tools, and integrations via the dashboard
- **Team Coordination** — Plans, A2A communication, and shared workspaces
- **Low Friction** — From idea to running agent in minutes

---

## Background Agents

Clawforce agents are **background workers** — they run 24/7 in isolated containers, triggered by cron, events, or channels. We want to keep it simple and run purely in the background. Therefore. We do **not** introduce:

- **Computer Use** — Direct mouse/keyboard control of desktops
- **Browser Use** — Automated browser driving (including headless mode)

---

## Best Practices

### 1. Security First

- **Use container isolation** — Docker/Podman per agent; avoid process runtime in production
- **Sandboxed mode** when possible — Read-only rootfs, no network for sensitive workloads
- **Secrets** — Use the vault; never hardcode API keys
- **Approval gates** — Enable `ask_before_run` for sensitive tools (`exec`, `write_file`, etc.)
- **Audit logs** — Capture and monitor `clawforce.audit` for security events

See [Security](/guide/security) for details.

### 2. Trusted Software & Registries

- **Software Registry** — Use trusted, curated software from the marketplace
- **MCP Registry** — Prefer official or internal MCP servers over arbitrary HTTP endpoints
- **Avoid unvetted tools** — Limit agents to software and MCPs you’ve reviewed

### 3. Use Internal MaaS (MCP-as-a-Service)

- **Internal MaaS** — Point agents to your internal MCP servers for governance, cost control, and compliance
- **LiteLLM** — Works with any OpenAI-compatible endpoint
- **Data residency** — Keeps prompts and responses within your infrastructure

### 4. Skills Registry

- **Reuse skills** — Use the Skills Registry to share capabilities across agents
- **Version control** — Treat skills as code; version and review changes
- **Custom skills** — Add domain-specific skills rather than overloading prompts

### 5. Plans for Team Coordination

- **Multi-agent work** — Use Plans (Kanban-style boards) when several agents collaborate
- **Clear boundaries** — Define roles and responsibilities per agent
- **External sync** — Pull tasks from GitHub, Jira, etc.; Plans orchestrate execution

### 6. Start Strict, Relax as Needed

- **Start sandboxed** — Test new agents in Safe mode first
- **Promote gradually** — Move to Standard (permissive) only when network/software is required
- **Privileged** — Reserve for trusted, controlled environments

### 7. Review & Iterate

- **Activity logs** — Regularly inspect agent behavior
- **Workspace artifacts** — Review outputs before trusting automation
- **Iterate on prompts** — Refine objectives based on real runs

---

## Summary

| Principle | Action |
|-----------|--------|
| Easy setup | Deploy from marketplace, configure via dashboard |
| Background-first | No Computer/Browser Use; use MCP for integrations |
| Security | Containers, vault, approval gates, audit logs |
| Trusted tooling | Curated software, MCP registry, internal MaaS (MCP-as-a-Service) |
| Skills & Plans | Skills Registry for reuse; Plans for team coordination |
| Gradual trust | Start sandboxed; relax only when necessary |

For more, see [Configuration](/guide/configuration), [Security](/guide/security), and [Plans](/guide/plans).
