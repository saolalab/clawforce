# Clawforce

[![PyPI version](https://badge.fury.io/py/clawforce.svg)](https://badge.fury.io/py/clawforce)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Multi-agent team admin and control plane. Build teams of AI agents that collaborate on real work.

## Installation

```bash
pip install clawforce
```

This installs everything you need, including all messaging channels.

## Quick Start

```bash
# 1. Initialize and create admin user
clawforce setup

# 2. Start the server
clawforce serve

# Access dashboard at http://localhost:8080
```

## Features

- **Multi-Agent Teams** — Coordinate multiple AI agents on shared goals
- **Plan Boards** — Kanban-style task management with automatic notifications
- **Agent-to-Agent Communication** — Agents discover and message each other
- **Real-Time Dashboard** — Live view of agent activity and progress
- **Agent Runtimes** — Run agents as subprocesses or Docker containers
- **REST API** — Full API for plans, agents, and artifacts

## CLI Commands

```bash
# Setup & Server
clawforce setup                    # Initialize and create admin user
clawforce serve                    # Start on port 8080
clawforce serve --port 3000        # Custom port
clawforce serve --workers 4        # Production with multiple workers

# Agent Management
clawforce agent list               # List all agents
clawforce agent create --name "Agent Name" --template sre
clawforce agent start <id>         # Start an agent
clawforce agent stop <id>          # Stop an agent
clawforce agent token <id>         # Show agent connection token
clawforce agent token <id> --regenerate  # Rotate agent token

# User Management
clawforce user create <username>   # Create user (--password, --role)
clawforce user update <username>   # Update user (--password, --role)
clawforce user list               # List admin users
clawforce user set-password <username>   # Reset password
clawforce user reset <username>   # Reset password (alias)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLAWFORCE                              │
│            Multi-Agent Admin & Control Plane                │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Plan Board │  │ Agent Runtimes│  │  WebSocket Hub   │   │
│  │  (Kanban)   │  │ (proc/docker)│  │ (req/resp + RT)  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                       CLAWBOT                               │
│              Lightweight Agent Workers                      │
├─────────────────────────────────────────────────────────────┤
│                       CLAWLIB                               │
│              Shared Infrastructure                          │
└─────────────────────────────────────────────────────────────┘
```

## Docker Deployment

```bash
docker run -d -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./data:/data \
  ghcr.io/saolalab/clawforce:latest
```

## Documentation

Full documentation: https://github.com/saolalab/clawforce

## License

Apache 2.0
