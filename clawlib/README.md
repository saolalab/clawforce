# clawlib

Shared technical library for the Clawforce ecosystem.

## Installation

```bash
pip install clawlib
```

## What's Included

- **Storage backends** — Local filesystem and S3 storage abstractions
- **Configuration** — Pydantic-based config schema and YAML/JSON loader
- **Activity tracking** — Event logging for agent activity streams
- **Registry** — Skill (agentskill.sh), MCP (official registry), and Software (marketplace YAML) registries

## Usage

This package is typically installed as a dependency of `clawbot` or `clawforce`. For direct usage:

```python
from clawlib.storage import get_storage_backend
from clawlib.config import load_config
from clawlib.activity import ActivityLog, ActivityEvent
```

## Part of Clawforce

This is a component of the [Clawforce](https://github.com/saolalab/clawforce) multi-agent platform.

- **clawlib** — Shared library (this package)
- **clawbot** — AI agent worker framework
- **clawforce** — Admin control plane and dashboard

## License

Apache 2.0
