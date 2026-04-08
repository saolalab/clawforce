# All-in-one Clawforce image: SPA + API; same image is used as agent worker pods.
# Build: docker build -t clawforce:latest -f deploy/Dockerfile .
#
# Deploy on k3s (see scripts/install.sh for the full deployment):
#   kubectl apply -f deploy/k8s/
#
# OAuth callback ports (e.g. 1455 for ChatGPT/Codex) are handled by short-lived sibling pods
# spawned on demand — no extra port configuration needed.

# Stage 1: Build React SPA (cache-friendly: deps first, then source)
FROM node:20-slim AS frontend
WORKDIR /app/clawforce-ui
COPY clawforce-ui/package.json clawforce-ui/package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY clawforce-ui/ ./
RUN mkdir -p /app/clawforce/static
RUN npm run build

# Stage 2: Final image (Python backend + SPA; runtime runs this same image as worker)
FROM node:20-slim AS node-base

FROM ubuntu:24.04

# Node.js (from node-base)
COPY --from=node-base /usr/local/bin/node /usr/local/bin/node
COPY --from=node-base /usr/local/lib /usr/local/lib
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx && \
    ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# Python 3.12, uv, and runtime deps (Ubuntu 24.04 has Python 3.12 in default repos)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl ca-certificates git \
      python3.12 python3.12-venv \
      ripgrep socat sudo && \
    rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager) via official installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Symlink python3 for uv (expects python3)
RUN ln -sf /usr/bin/python3.12 /usr/bin/python3

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Dependencies + source
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY clawlib/pyproject.toml clawlib/README.md clawlib/
COPY clawbot/pyproject.toml clawbot/README.md clawbot/
COPY clawforce/pyproject.toml clawforce/README.md clawforce/
COPY clawlib/ clawlib/
COPY clawbot/ clawbot/
COPY clawforce/ clawforce/
COPY marketplace/ marketplace/
RUN uv sync --no-dev

# SPA static files (from frontend stage)
COPY --from=frontend /app/clawforce/static /app/clawforce/static

# Entrypoint
COPY deploy/entrypoint.sh /app/deploy/entrypoint.sh
RUN chmod +x /app/deploy/entrypoint.sh

# Runtime config
ENV ADMIN_STORAGE_ROOT=/data
ENV ADMIN_RUNTIME_BACKEND=k8s
# Redirect XDG user-data dir under /data so OAuth tokens (and any other
# platformdirs-managed state) survive pod recreation.
ENV XDG_DATA_HOME=/data/.local/share

# Default admin credentials for first-run setup (set in entrypoint to avoid ENV secret warning).
# Override: kubectl set env deployment/clawforce ADMIN_SETUP_USERNAME=admin ADMIN_SETUP_PASSWORD=...

# Worker image: published builds set this at CI time; local builds use clawforce:latest.
# Workers get an isolated hostPath bind mount (data/agents/{id}) via k8s pod spec.
# Set AGENT_STORAGE_HOST_PATH to the host directory mounted at /data.
ENV AGENT_IMAGE=ghcr.io/saolalab/clawforce:latest
# Admin URL visible to worker pods — use k8s service DNS within the cluster.
ENV ADMIN_PUBLIC_URL=http://clawforce.clawforce.svc.cluster.local:8080
# k8s namespace for agent pods and OAuth callback pods.
ENV K8S_NAMESPACE=clawforce
RUN mkdir -p /data
VOLUME /data

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["clawforce", "serve", "--host", "0.0.0.0", "--port", "8080", "--data-dir", "/data"]
