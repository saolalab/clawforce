#!/usr/bin/env bash
#
# Local Docker dev workflow: rebuild image, cleanup old containers, run fresh.
#
# Usage:
#   ./scripts/dev.sh              # full rebuild + run
#   ./scripts/dev.sh --no-build   # skip build, just restart container
#   ./scripts/dev.sh --clean      # stop everything + remove data volume
#   ./scripts/dev.sh --logs       # tail logs after starting
#
set -euo pipefail

# ── Config (override via env) ────────────────────────────────────────────────
IMAGE="${IMAGE:-clawforce:latest}"
CONTAINER="${CONTAINER:-clawforce}"
DATA_DIR="${DATA_DIR:-./data}"
PORT="${PORT:-8080}"
ADMIN_USER="${ADMIN_SETUP_USERNAME:-admin}"
ADMIN_PASS="${ADMIN_SETUP_PASSWORD:-admin}"
# Stable JWT secret so browser tokens survive container restarts.
# Override via env for production; this default is fine for local dev.
JWT_SECRET="${ADMIN_JWT_SECRET:-clawforce-local-dev-secret-do-not-use-in-prod}"

# ── Container engine: docker (default) or podman ────────────────────────────
if [ -n "$CLAWFORCE_ENGINE" ]; then
    ENGINE="$CLAWFORCE_ENGINE"
elif command -v docker &>/dev/null; then
    ENGINE="docker"
elif command -v podman &>/dev/null; then
    ENGINE="podman"
else
    echo "Error: neither docker nor podman found in PATH"
    exit 1
fi

# ── Flags ────────────────────────────────────────────────────────────────────
DO_BUILD=true
DO_CLEAN_DATA=false
DO_LOGS=false

for arg in "$@"; do
  case "$arg" in
    --no-build)  DO_BUILD=false ;;
    --clean)     DO_CLEAN_DATA=true ;;
    --logs)      DO_LOGS=true ;;
    -h|--help)
      echo "Usage: $0 [--no-build] [--clean] [--logs]"
      echo ""
      echo "  --no-build   Skip Docker image build (reuse existing image)"
      echo "  --clean      Remove data directory (fresh start, wipes agents/config)"
      echo "  --logs       Tail container logs after starting"
      echo ""
      echo "Environment overrides:"
      echo "  IMAGE=...              Container image name  (default: clawforce:latest)"
      echo "  PORT=...               Host port             (default: 8080)"
      echo "  ADMIN_JWT_SECRET=...   JWT signing secret    (stable default for local dev)"
      echo "  PROCESS_POOL=true      Use process pool instead of container isolation"
      echo "  CLAWFORCE_ENGINE=...   Container engine: docker or podman (default: auto-detect)"
      exit 0
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Helpers ──────────────────────────────────────────────────────────────────
info()  { printf "\033[1;34m▸ %s\033[0m\n" "$*"; }
ok()    { printf "\033[1;32m✓ %s\033[0m\n" "$*"; }
warn()  { printf "\033[1;33m⚠ %s\033[0m\n" "$*"; }

stop_container() {
  local name="$1"
  if $ENGINE inspect "$name" &>/dev/null; then
    info "Stopping $name ..."
    $ENGINE stop "$name" 2>/dev/null || true
    $ENGINE rm -f "$name" 2>/dev/null || true
    ok "Removed $name"
  fi
}

# ── Pre-flight: container engine ─────────────────────────────────────────────
if ! $ENGINE info &>/dev/null; then
  warn "$ENGINE is not running. Please start it and retry."
  exit 1
fi

# ── Stop agent worker containers (clawbot-agent-*) ──────────────────────────
AGENT_CONTAINERS=$($ENGINE ps -aq --filter "name=clawbot-agent-" 2>/dev/null || true)
if [ -n "$AGENT_CONTAINERS" ]; then
  info "Stopping orphaned agent worker containers ..."
  echo "$AGENT_CONTAINERS" | xargs $ENGINE rm -f 2>/dev/null || true
  ok "Agent workers cleaned up"
fi

# ── Stop main container ─────────────────────────────────────────────────────
stop_container "$CONTAINER"

# Also kill any container using our port (unnamed runs from earlier)
PORT_CONTAINER=$($ENGINE ps -q --filter "publish=$PORT" 2>/dev/null || true)
if [ -n "$PORT_CONTAINER" ]; then
  info "Stopping container(s) on port $PORT ..."
  echo "$PORT_CONTAINER" | xargs $ENGINE rm -f 2>/dev/null || true
fi

# ── Resolve DATA_DIR to absolute path ────────────────────────────────────────
DATA_DIR="$(cd "$PROJECT_ROOT" && mkdir -p "$DATA_DIR" && cd "$DATA_DIR" && pwd)"

# ── Optional: wipe data directory ────────────────────────────────────────────
if $DO_CLEAN_DATA; then
  warn "Removing data directory $DATA_DIR (all agent data will be lost) ..."
  rm -rf "$DATA_DIR"
  mkdir -p "$DATA_DIR"
  ok "Data directory wiped"
fi

# ── Build ────────────────────────────────────────────────────────────────────
if $DO_BUILD; then
  info "Building $IMAGE ..."
  $ENGINE build -t "$IMAGE" -f "$PROJECT_ROOT/deploy/Dockerfile" "$PROJECT_ROOT"
  ok "Image built: $IMAGE"
else
  info "Skipping build (--no-build)"
fi

# ── Run ──────────────────────────────────────────────────────────────────────
info "Starting $CONTAINER on port $PORT ..."

RUN_ARGS=(
  -d
  -p "$PORT:8080"
  -e ADMIN_SETUP_USERNAME="$ADMIN_USER"
  -e ADMIN_SETUP_PASSWORD="$ADMIN_PASS"
  -e ADMIN_JWT_SECRET="$JWT_SECRET"
  -e AGENT_IMAGE="$IMAGE"
  -e AGENT_STORAGE_HOST_PATH="$DATA_DIR"
  -v "$DATA_DIR":/data
  --name "$CONTAINER"
)

# Docker needs explicit host mapping; podman resolves host.docker.internal natively
if [ "$ENGINE" = "docker" ]; then
  RUN_ARGS+=(--add-host host.docker.internal:host-gateway)
fi

if [ "${PROCESS_POOL:-false}" = "true" ]; then
    info "Using process pool (no container isolation for agents)"
    RUN_ARGS+=(-e "ADMIN_RUNTIME_BACKEND=process")
else
    info "Using container pool (one container per agent)"
    RUN_ARGS+=(-e "ADMIN_RUNTIME_BACKEND=docker")
    if [ "$ENGINE" = "podman" ]; then
        # Detect podman socket path to mount into the admin container.
        # macOS: containers run inside a Linux VM. The host-side socket
        #   (e.g. /var/folders/.../podman-machine-default-api.sock) is NOT
        #   visible inside the VM. We must use the in-VM path instead.
        # Linux: the socket is directly on the host filesystem.
        if [ "$(uname -s)" = "Darwin" ]; then
            # Rootful VM: /run/podman/podman.sock   Rootless VM: /run/user/1000/podman/podman.sock
            PODMAN_ROOTFUL=$(podman machine inspect --format '{{.Rootful}}' 2>/dev/null || echo "true")
            if [ "$PODMAN_ROOTFUL" = "true" ]; then
                SOCK_PATH="/run/podman/podman.sock"
            else
                SOCK_PATH="/run/user/1000/podman/podman.sock"
            fi
            info "Using podman in-VM socket: $SOCK_PATH"
        else
            SOCK_PATH="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
            if [ ! -S "$SOCK_PATH" ]; then
                warn "Podman socket not found at $SOCK_PATH"
                warn "Ensure podman is running: systemctl --user enable --now podman.socket"
                exit 1
            fi
            info "Using podman socket: $SOCK_PATH"
        fi
        RUN_ARGS+=(-v "$SOCK_PATH:/var/run/docker.sock")
        RUN_ARGS+=(--security-opt label=disable)
    else
        RUN_ARGS+=(-v "/var/run/docker.sock:/var/run/docker.sock")
    fi
fi

$ENGINE run "${RUN_ARGS[@]}" "$IMAGE"

# ── Health check ─────────────────────────────────────────────────────────────
info "Waiting for server to be ready ..."
for i in $(seq 1 15); do
  if curl -sf "http://localhost:$PORT/api/health" &>/dev/null; then
    ok "Server is up at http://localhost:$PORT"
    break
  fi
  if [ "$i" -eq 15 ]; then
    warn "Server not responding after 15s — check logs: $ENGINE logs $CONTAINER"
  fi
  sleep 1
done

# ── Optional: tail logs ──────────────────────────────────────────────────────
if $DO_LOGS; then
  echo ""
  info "Tailing logs (Ctrl+C to stop) ..."
  $ENGINE logs -f "$CONTAINER"
fi
