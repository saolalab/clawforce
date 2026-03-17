# Claw Templates — Autonomous Company Roles

Pre-built role templates for bootstrapping an autonomous AI company.
Each role is a self-contained agent profile with personality, instructions,
domain skills, and a tailored workspace.

**Default template** (used when no role is specified) lives at
`marketplace/roles/default/profile` and `marketplace/roles/default/workspace`.
Role templates live under `marketplace/roles/{role}/profile` and
`marketplace/roles/{role}/workspace`.

## Roles

| Role | Directory | Focus |
|------|-----------|-------|
| CEO | `ceo/` | Strategic vision, cross-team coordination, investor relations |
| CTO | `cto/` | Technical architecture, engineering culture, build-vs-buy |
| SRE | `sre/` | Reliability, monitoring, incident response, infrastructure |
| Software Engineer | `software-engineer/` | Code quality, feature delivery, testing |
| Product Manager | `product-manager/` | Roadmap, user research, prioritization |
| Finance Controller | `finance-controller/` | Bookkeeping, budgets, financial reporting |
| HR Manager | `hr-manager/` | Recruiting, onboarding, culture, compliance |
| Marketing Lead | `marketing-lead/` | Brand, content, campaigns, growth metrics |
| Legal Counsel | `legal-counsel/` | Contracts, IP, regulatory compliance, risk |
| Data Analyst | `data-analyst/` | BI dashboards, data pipelines, insights |
| Customer Support Lead | `customer-support-lead/` | Customer success, support tickets, feedback |
| Security Engineer | `security-engineer/` | AppSec, vulnerability management, penetration testing |
| DevOps Engineer | `devops-engineer/` | CI/CD pipelines, deployment automation, infrastructure as code |
| UX Designer | `ux-designer/` | User experience, design systems, usability testing |
| QA Engineer | `qa-engineer/` | Test automation, quality assurance, bug management |
| Technical Writer | `technical-writer/` | API documentation, user guides, knowledge base |
| Sales Lead | `sales-lead/` | Pipeline management, customer acquisition, partnerships |
| Business Analyst | `business-analyst/` | Requirements gathering, process improvement, stakeholder alignment |
| Project Manager | `project-manager/` | Project tracking, resource management, delivery |
| Solution Architect | `solution-architect/` | Customer solutions, integrations, technical pre-sales |

## Template Structure

Each role follows the standard profile layout. **TOOLS.md** and **USER.md** use the same content as the default template. **AGENTS.md** holds role-specific instructions (concise responsibilities and guidelines).

```
<role>/
├── profile/
│   ├── AGENTS.md        # Role intro, core responsibilities, guidelines
│   ├── TOOLS.md         # Same as default (full tool docs, cron, heartbeat, planning)
│   ├── config/
│   │   └── agent.yaml   # Model, temperature, tool settings
│   └── skills/          # Domain-specific skills
└── workspace/
    ├── README.md        # Same as default
    ├── HEARTBEAT.md     # Provisioned to .agents/HEARTBEAT.md
    └── memory/          # Provisioned to .agents/memory/
        ├── MEMORY.md    # Long-term memory
        └── HISTORY.md   # Event log
```

## Usage

When provisioning a new agent, specify the role template:

```bash
clawforce agent create --name "alice" --template sre
clawforce agent create --name "bob" --template finance-controller
clawforce agent create --name "alice" --template sre --mode process   # run as subprocess
clawforce agent create --name "ops" --template sre --mode docker      # run in container
```

- **`--template`** — Role template (e.g. `sre`, `ceo`). Omit to use the default profile/workspace.
- **`--mode`** — Execution mode: `process` (one subprocess per agent) or `docker` (one container per agent). Omit to use the app's default pool backend.

The provisioner copies the role's `profile/` and `workspace/` into the
agent's directory, then converts `config/agent.yaml` to `.config/agent.json`.

## Inter-Agent Communication

Agents communicate via the `message` tool. Each role template includes
an `a2a` (agent-to-agent) skill that documents the communication protocol
and the other roles in the company. Agents can delegate tasks, request
information, and escalate issues to the appropriate peer.

## Customization

These templates are starting points. After provisioning, each agent's
workspace is fully editable — you can refine AGENTS.md, add skills,
adjust heartbeat tasks, and tune model parameters per agent.
