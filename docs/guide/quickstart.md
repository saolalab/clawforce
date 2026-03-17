# Quick Start

The fastest way to get started with Clawforce.

## One-Line Install (Recommended)

Installs Docker (if needed) and runs Clawforce:

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash
```

**Windows (PowerShell as Administrator):**
```powershell
irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 | iex
```

After installation, open **http://localhost:8080** and log in with `admin`/`admin`.

> **Security:** Change the default password immediately after first login, or pass `--admin-pass <yourpassword>` to the installer.

**You're ready to deploy your first agent from the marketplace.**

## Install Options

```bash
# Custom port and admin password
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --port 9000 --admin-pass mypassword

# Use process runtime instead of Docker isolation
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --process-runtime

# Uninstall
curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --uninstall
```

## Run by Docker command

Maximum security — each agent runs in its own isolated Docker container:

```bash
docker run -d -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $HOME/.clawforce-data:/data \
  -e AGENT_STORAGE_HOST_PATH=$HOME/.clawforce-data \
  ghcr.io/saolalab/clawforce:latest
```

## Native Install

```bash
pip install git+https://github.com/saolalab/clawforce.git
clawforce setup
clawforce serve
```

## Next Steps

- [Configuration](/guide/configuration) — Environment variables and settings
- [Channels](/guide/channels) — Connect Slack, Telegram, Discord, and more
