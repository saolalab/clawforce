# clawbot

A lightweight AI agent framework modified from nanobot, featuring tools, messaging channels, and LLM providers.

## Installation

```bash
pip install clawbot
```

**With messaging channels:**

```bash
pip install clawbot[telegram]      # Telegram support
pip install clawbot[slack]         # Slack support
pip install clawbot[all-channels]  # All channels
```

See [docs/CHANNELS_SETUP.md](../docs/CHANNELS_SETUP.md) for channel-specific setup (Slack, etc.).

## Features

- **Agent Tools** — Filesystem, shell, web search, MCP integration
- **Messaging Channels** — Telegram, Slack, Discord, Feishu, WhatsApp, Email
- **LLM Providers** — Any provider via LiteLLM (OpenAI, Anthropic, etc.)
- **Skills System** — Extensible agent capabilities
- **Cron Scheduling** — Recurring tasks and heartbeats

## Quick Start

```bash
# Initialize a new agent
clawbot init ./my-agent

# Start the agent worker
clawbot run --agent-root ./my-agent
```

## CLI Commands

```bash
clawbot init <path>                          # Create agent directory
clawbot run --agent-root <path>              # Start agent worker
clawbot run --agent-root <path> \
  --admin-url <url> --token <token>          # Connect to a Clawforce control plane
clawbot config --agent-root <path>           # View agent configuration
clawbot config --agent-root <path> --edit    # Open config in editor
clawbot version                              # Show version
```

## Part of Clawforce

This is a component of the [Clawforce](https://github.com/saolalab/clawforce) multi-agent platform.

For team coordination with multiple agents, plans, and a web dashboard, install:

```bash
pip install clawforce
```

## License

Apache 2.0
