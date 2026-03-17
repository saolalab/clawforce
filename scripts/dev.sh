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
      echo "  IMAGE=...              Docker image name  (default: clawforce:latest)"
      echo "  PORT=...               Host port          (default: 8080)"
      echo "  ADMIN_JWT_SECRET=...   JWT signing secret (stable default for local dev)"
      echo "  PROCESS_POOL=true      Use process pool instead of Docker (no socket needed)"
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
  if docker inspect "$name" &>/dev/null; then
    info "Stopping $name ..."
    docker stop "$name" 2>/dev/null || true
    docker rm -f "$name" 2>/dev/null || true
    ok "Removed $name"
  fi
}

# ── Pre-flight: Docker daemon ────────────────────────────────────────────────
if ! docker info &>/dev/null; then
  warn "Docker daemon is not running. Please start Docker Desktop and retry."
  exit 1
fi

# ── Stop agent worker containers (clawbot-agent-*) ──────────────────────────
AGENT_CONTAINERS=$(docker ps -aq --filter "name=clawbot-agent-" 2>/dev/null || true)
if [ -n "$AGENT_CONTAINERS" ]; then
  info "Stopping orphaned agent worker containers ..."
  echo "$AGENT_CONTAINERS" | xargs docker rm -f 2>/dev/null || true
  ok "Agent workers cleaned up"
fi

# ── Stop main container ─────────────────────────────────────────────────────
stop_container "$CONTAINER"

# Also kill any container using our port (unnamed runs from earlier)
PORT_CONTAINER=$(docker ps -q --filter "publish=$PORT" 2>/dev/null || true)
if [ -n "$PORT_CONTAINER" ]; then
  info "Stopping container(s) on port $PORT ..."
  echo "$PORT_CONTAINER" | xargs docker rm -f 2>/dev/null || true
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
  docker build -t "$IMAGE" -f "$PROJECT_ROOT/deploy/Dockerfile" "$PROJECT_ROOT"
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
  --add-host host.docker.internal:host-gateway
)

if [ "${PROCESS_POOL:-false}" = "true" ]; then
    info "Using process pool (no Docker isolation for agents)"
    RUN_ARGS+=(-e "ADMIN_RUNTIME_BACKEND=process")
else
    info "Using Docker pool (one container per agent)"
    RUN_ARGS+=(-e "ADMIN_RUNTIME_BACKEND=docker")
    RUN_ARGS+=(-v "/var/run/docker.sock:/var/run/docker.sock") # this is mount to admin, not agents (agents will use the socket in their own container)
fi

docker run "${RUN_ARGS[@]}" "$IMAGE"

# ── Health check ─────────────────────────────────────────────────────────────
info "Waiting for server to be ready ..."
for i in $(seq 1 15); do
  if curl -sf "http://localhost:$PORT/api/health" &>/dev/null; then
    ok "Server is up at http://localhost:$PORT"
    break
  fi
  if [ "$i" -eq 15 ]; then
    warn "Server not responding after 15s — check logs: docker logs $CONTAINER"
  fi
  sleep 1
done

# ── Optional: tail logs ──────────────────────────────────────────────────────
if $DO_LOGS; then
  echo ""
  info "Tailing logs (Ctrl+C to stop) ..."
  docker logs -f "$CONTAINER"
fi
