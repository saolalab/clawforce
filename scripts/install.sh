#!/usr/bin/env bash
#
# Clawforce Installer
# 
# One-line install:
#   curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash
#
# Or with custom options:
#   curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --port 9000 --data ~/my-data
#
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration (override via environment or flags)
# ─────────────────────────────────────────────────────────────────────────────
IMAGE="${CLAWFORCE_IMAGE:-ghcr.io/saolalab/clawforce:latest}"
CONTAINER="${CLAWFORCE_CONTAINER:-clawforce}"
DATA_DIR="${CLAWFORCE_DATA:-$HOME/.clawforce-data}"
PORT="${CLAWFORCE_PORT:-8080}"
ADMIN_USER="${CLAWFORCE_ADMIN_USER:-admin}"
ADMIN_PASS="${CLAWFORCE_ADMIN_PASS:-admin}"
SKIP_DOCKER_INSTALL="${CLAWFORCE_SKIP_DOCKER:-false}"
PROCESS_RUNTIME="${CLAWFORCE_PROCESS_RUNTIME:-${CLAWFORCE_PROCESS_POOL:-false}}"
# Container engine: docker (default) or podman
ENGINE="${CLAWFORCE_ENGINE:-}"

# ─────────────────────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────
show_help() {
    cat << EOF
Clawforce Installer

Usage: install.sh [OPTIONS]

Options:
  --port PORT           Port to expose (default: 8080)
  --data DIR            Data directory (default: ~/.clawforce/data)
  --admin-user USER     Admin username (default: admin)
  --admin-pass PASS     Admin password (default: admin)
  --engine ENGINE       Container engine: docker or podman (default: auto-detect)
  --process-runtime     Use process runtime instead of container isolation (alias: --process-pool)
  --skip-docker         Skip Docker/Podman installation check
  --uninstall           Remove Clawforce container and optionally data
  -h, --help            Show this help message

Environment variables:
  CLAWFORCE_IMAGE       Container image (default: ghcr.io/saolalab/clawforce:latest)
  CLAWFORCE_ENGINE      Container engine: docker or podman (default: auto-detect)
  CLAWFORCE_PORT        Port to expose
  CLAWFORCE_DATA        Data directory path
  CLAWFORCE_ADMIN_USER  Admin username
  CLAWFORCE_ADMIN_PASS  Admin password

Examples:
  # Quick install with defaults
  curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash

  # Custom port and data directory
  curl -fsSL ... | bash -s -- --port 9000 --data /opt/clawforce

  # With custom admin credentials
  curl -fsSL ... | bash -s -- --admin-user myuser --admin-pass mypassword

EOF
    exit 0
}

UNINSTALL=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)         PORT="$2"; shift 2 ;;
        --data)         DATA_DIR="$2"; shift 2 ;;
        --admin-user)   ADMIN_USER="$2"; shift 2 ;;
        --admin-pass)   ADMIN_PASS="$2"; shift 2 ;;
        --engine)       ENGINE="$2"; shift 2 ;;
        --process-pool|--process-runtime) PROCESS_RUNTIME=true; shift ;;
        --skip-docker)  SKIP_DOCKER_INSTALL=true; shift ;;
        --uninstall)    UNINSTALL=true; shift ;;
        -h|--help)      show_help ;;
        *)              echo "Unknown option: $1"; show_help ;;
    esac
done

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { printf "${BLUE}▸${NC} %s\n" "$*"; }
success() { printf "${GREEN}✓${NC} %s\n" "$*"; }
warn()    { printf "${YELLOW}⚠${NC} %s\n" "$*"; }
error()   { printf "${RED}✗${NC} %s\n" "$*" >&2; }
die()     { error "$*"; exit 1; }

command_exists() {
    command -v "$1" &> /dev/null
}

detect_os() {
    case "$(uname -s)" in
        Linux*)  echo "linux" ;;
        Darwin*) echo "macos" ;;
        *)       echo "unknown" ;;
    esac
}

detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64)  echo "amd64" ;;
        aarch64|arm64) echo "arm64" ;;
        *)             echo "unknown" ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Auto-detect container engine
# ─────────────────────────────────────────────────────────────────────────────
if [ -z "$ENGINE" ]; then
    if command_exists docker; then
        ENGINE="docker"
    elif command_exists podman; then
        ENGINE="podman"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Uninstall
# ─────────────────────────────────────────────────────────────────────────────
if $UNINSTALL; then
    if [ -z "$ENGINE" ]; then
        die "Neither docker nor podman found. Nothing to uninstall."
    fi
    info "Uninstalling Clawforce..."

    # Stop and remove container
    if $ENGINE inspect "$CONTAINER" &>/dev/null; then
        info "Stopping container..."
        $ENGINE stop "$CONTAINER" 2>/dev/null || true
        $ENGINE rm "$CONTAINER" 2>/dev/null || true
        success "Container removed"
    else
        info "Container not found"
    fi

    # Stop agent workers
    AGENT_CONTAINERS=$($ENGINE ps -aq --filter "name=clawbot-agent-" 2>/dev/null || true)
    if [ -n "$AGENT_CONTAINERS" ]; then
        info "Stopping agent workers..."
        echo "$AGENT_CONTAINERS" | xargs $ENGINE rm -f 2>/dev/null || true
        success "Agent workers removed"
    fi
    
    # Ask about data
    if [ -d "$DATA_DIR" ]; then
        echo ""
        printf "Remove data directory %s? [y/N]: " "$DATA_DIR"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            rm -rf "$DATA_DIR"
            success "Data directory removed"
        else
            info "Data directory kept at $DATA_DIR"
        fi
    fi
    
    success "Clawforce uninstalled"
    exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║                                                      ║"
echo "  ║    - CLAWFORCE -                                     ║"
echo "  ║    Autonomous AI Team Orchestration Platform         ║"
echo "  ║                                                      ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""

OS=$(detect_os)
ARCH=$(detect_arch)
info "Detected: $OS ($ARCH)"
if [ -n "$ENGINE" ]; then
    info "Container engine: $ENGINE"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Container Engine Installation
# ─────────────────────────────────────────────────────────────────────────────
install_podman_linux() {
    info "Installing Podman on Linux..."

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    else
        DISTRO="unknown"
    fi

    case "$DISTRO" in
        ubuntu|debian|linuxmint|pop)
            sudo apt-get update
            sudo apt-get install -y podman
            ;;
        fedora|rhel|centos|rocky|almalinux)
            sudo dnf install -y podman 2>/dev/null || sudo yum install -y podman
            ;;
        arch|manjaro)
            sudo pacman -Sy --noconfirm podman
            ;;
        *)
            die "Unsupported distro for automatic Podman install. Please install Podman manually."
            ;;
    esac
    success "Podman installed"
}

install_podman_macos() {
    if command_exists brew; then
        info "Installing Podman via Homebrew..."
        brew install podman
        info "Initializing Podman machine..."
        podman machine init 2>/dev/null || true
        podman machine start 2>/dev/null || true
        success "Podman installed"
    else
        die "Please install Homebrew first, then run: brew install podman"
    fi
}

install_docker_linux() {
    info "Installing Docker on Linux..."
    
    # Detect Linux distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    else
        DISTRO="unknown"
    fi
    
    case "$DISTRO" in
        ubuntu|debian|linuxmint|pop)
            info "Using apt package manager..."
            sudo apt-get update
            sudo apt-get install -y ca-certificates curl gnupg
            sudo install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$DISTRO/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || true
            sudo chmod a+r /etc/apt/keyrings/docker.gpg
            echo \
              "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$DISTRO \
              $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
              sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt-get update
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        fedora|rhel|centos|rocky|almalinux)
            info "Using dnf/yum package manager..."
            sudo dnf -y install dnf-plugins-core 2>/dev/null || sudo yum -y install yum-utils
            sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo 2>/dev/null || \
                sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>/dev/null || \
                sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        arch|manjaro)
            info "Using pacman package manager..."
            sudo pacman -Sy --noconfirm docker docker-compose
            ;;
        *)
            info "Using convenience script for unknown distro..."
            curl -fsSL https://get.docker.com | sudo sh
            ;;
    esac
    
    # Start Docker service
    sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null || true
    sudo systemctl enable docker 2>/dev/null || true
    
    # Add current user to docker group
    if ! groups | grep -q docker; then
        sudo usermod -aG docker "$USER"
        warn "Added $USER to docker group. You may need to log out and back in."
        warn "For now, running with sudo..."
        NEED_SUDO=true
    fi
}

install_docker_macos() {
    info "Docker Desktop is required on macOS"
    
    if command_exists brew; then
        info "Installing via Homebrew..."
        brew install --cask docker
        success "Docker Desktop installed"
        echo ""
        warn "Please open Docker Desktop to complete setup, then run this script again."
        echo ""
        echo "  1. Open Docker Desktop from Applications"
        echo "  2. Complete the setup wizard"
        echo "  3. Wait for Docker to start (whale icon in menu bar)"
        echo "  4. Run this installer again"
        echo ""
        exit 0
    else
        echo ""
        error "Docker Desktop is not installed."
        echo ""
        echo "  Please install Docker Desktop from:"
        echo "  https://docs.docker.com/desktop/install/mac-install/"
        echo ""
        echo "  Or install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo ""
        exit 1
    fi
}

check_and_install_engine() {
    if $SKIP_DOCKER_INSTALL; then
        info "Skipping container engine check (--skip-docker)"
        return 0
    fi

    # If engine is already set and available, check if it's running
    if [ -n "$ENGINE" ] && command_exists "$ENGINE"; then
        if $ENGINE info &>/dev/null; then
            success "$ENGINE is installed and running"
            return 0
        else
            warn "$ENGINE is installed but not running"

            case "$OS" in
                linux)
                    if [ "$ENGINE" = "docker" ]; then
                        info "Starting Docker service..."
                        sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null || true
                    else
                        info "Starting Podman service..."
                        systemctl --user start podman.socket 2>/dev/null || true
                    fi
                    sleep 2
                    ;;
                macos)
                    if [ "$ENGINE" = "podman" ]; then
                        info "Starting Podman machine..."
                        podman machine start 2>/dev/null || true
                        sleep 2
                    else
                        echo ""
                        warn "Please start Docker Desktop and run this script again."
                        echo ""
                        exit 1
                    fi
                    ;;
            esac

            if $ENGINE info &>/dev/null; then
                success "$ENGINE started"
                return 0
            else
                die "Could not start $ENGINE. Please start it manually and try again."
            fi
        fi
    fi

    # Engine not installed — try to install
    echo ""
    if [ "$ENGINE" = "podman" ]; then
        warn "Podman is not installed."
        printf "Install Podman now? [Y/n]: "
        read -r response
        if [[ ! "$response" =~ ^[Nn]$ ]]; then
            case "$OS" in
                linux)  install_podman_linux ;;
                macos)  install_podman_macos ;;
                *)      die "Unsupported OS. Please install Podman manually." ;;
            esac
        else
            die "Podman is required. Please install it and try again."
        fi
    else
        # Default: install docker
        ENGINE="docker"
        warn "Docker is not installed."
        printf "Install Docker now? [Y/n]: "
        read -r response
        if [[ ! "$response" =~ ^[Nn]$ ]]; then
            case "$OS" in
                linux)  install_docker_linux ;;
                macos)  install_docker_macos ;;
                *)      die "Unsupported OS. Please install Docker manually." ;;
            esac
        else
            die "Docker is required. Please install it and try again."
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────────────────────────────────────
NEED_SUDO=false
check_and_install_engine

# Check if we need sudo for the engine
if ! $ENGINE info &>/dev/null 2>&1; then
    if sudo $ENGINE info &>/dev/null 2>&1; then
        NEED_SUDO=true
        if [ "$ENGINE" = "docker" ]; then
            warn "Docker requires sudo. Consider adding your user to the docker group."
        else
            warn "Podman requires sudo. Consider using rootless mode."
        fi
    else
        die "Cannot connect to $ENGINE"
    fi
fi

engine_cmd() {
    if $NEED_SUDO; then
        sudo $ENGINE "$@"
    else
        $ENGINE "$@"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Stop existing containers
# ─────────────────────────────────────────────────────────────────────────────
if engine_cmd inspect "$CONTAINER" &>/dev/null; then
    info "Stopping existing Clawforce container..."
    engine_cmd stop "$CONTAINER" 2>/dev/null || true
    engine_cmd rm "$CONTAINER" 2>/dev/null || true
fi

# Stop any orphaned agent workers
AGENT_CONTAINERS=$(engine_cmd ps -aq --filter "name=clawbot-agent-" 2>/dev/null || true)
if [ -n "$AGENT_CONTAINERS" ]; then
    info "Cleaning up agent workers..."
    echo "$AGENT_CONTAINERS" | xargs engine_cmd rm -f 2>/dev/null || true
fi

# ─────────────────────────────────────────────────────────────────────────────
# Create data directory
# ─────────────────────────────────────────────────────────────────────────────
info "Setting up data directory: $DATA_DIR"
mkdir -p "$DATA_DIR"

# Convert to absolute path
DATA_DIR="$(cd "$DATA_DIR" && pwd)"

# ─────────────────────────────────────────────────────────────────────────────
# Registry login check
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Pull image
# ─────────────────────────────────────────────────────────────────────────────
info "Pulling Clawforce image: $IMAGE"
engine_cmd pull "$IMAGE"
success "Image pulled"

# ─────────────────────────────────────────────────────────────────────────────
# Install CLI Wrapper
# ─────────────────────────────────────────────────────────────────────────────
install_cli_wrapper() {
    info "Installing 'clawforce' CLI wrapper..."
    local install_dir="$HOME/.local/bin"
    local wrapper_path="$install_dir/clawforce"

    # Ensure we're in a valid directory (avoids "chdir: cannot access parent" when cwd is stale)
    cd "${TMPDIR:-/tmp}" 2>/dev/null || cd /tmp 2>/dev/null || true

    mkdir -p "$install_dir"

    local tmpfile
    tmpfile="$(mktemp)" || { warn "Could not create temp file. Skipping CLI wrapper."; return 1; }
    cat > "$tmpfile" << 'EOF'
#!/usr/bin/env bash
# clawforce - Manage the Clawforce container

CONTAINER="${CLAWFORCE_CONTAINER:-clawforce}"

# Container engine: docker (default) or podman
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

show_help() {
    echo "Usage: clawforce <command>"
    echo ""
    echo "Commands:"
    echo "  start     Start the Clawforce container"
    echo "  stop      Stop the Clawforce container"
    echo "  clean     Stop and remove the Clawforce container"
    echo "  restart   Restart the Clawforce container"
    echo "  update    Pull the latest image and recreate the container"
    echo "  logs      View container logs"
    echo "  status    Check container status"
    echo ""
    echo "Environment:"
    echo "  CLAWFORCE_ENGINE   Container engine to use: docker or podman (default: auto-detect)"
}

if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

case "$1" in
    start)
        echo "Starting $CONTAINER..."
        $ENGINE start "$CONTAINER"
        ;;
    stop)
        echo "Stopping $CONTAINER..."
        $ENGINE stop "$CONTAINER"
        ;;
    clean)
        echo "Cleaning $CONTAINER..."
        $ENGINE stop "$CONTAINER" 2>/dev/null || true
        $ENGINE rm "$CONTAINER" 2>/dev/null || true
        echo "Cleaned."
        ;;
    restart)
        echo "Restarting $CONTAINER..."
        $ENGINE restart "$CONTAINER"
        ;;
    update)
        if ! $ENGINE inspect "$CONTAINER" &>/dev/null; then
            echo "Container '$CONTAINER' not found. Run the installer first."
            exit 1
        fi
        IMAGE=$($ENGINE inspect --format '{{.Config.Image}}' "$CONTAINER")
        echo "Pulling $IMAGE..."
        $ENGINE pull "$IMAGE"
        echo "Recreating $CONTAINER..."
        # Capture existing run config before removing
        PORTS=$($ENGINE inspect --format '{{range $p, $conf := .HostConfig.PortBindings}}{{(index $conf 0).HostPort}}:{{$p}} {{end}}' "$CONTAINER" | tr -d '/')
        DATA_VOL=$($ENGINE inspect --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Source}}{{end}}{{end}}' "$CONTAINER")
        ENVS=$($ENGINE inspect --format '{{range .Config.Env}}-e {{.}} {{end}}' "$CONTAINER")
        HAS_SOCK=$($ENGINE inspect --format '{{range .Mounts}}{{.Source}}{{end}}' "$CONTAINER" | grep -c "docker.sock\|podman.sock" || true)
        $ENGINE stop "$CONTAINER" 2>/dev/null || true
        $ENGINE rm "$CONTAINER"
        RUN_CMD="$ENGINE run -d --name $CONTAINER --restart unless-stopped"
        for p in $PORTS; do RUN_CMD="$RUN_CMD -p $p"; done
        if [ -n "$DATA_VOL" ]; then RUN_CMD="$RUN_CMD -v $DATA_VOL:/data"; fi
        if [ "$HAS_SOCK" -gt 0 ]; then RUN_CMD="$RUN_CMD -v /var/run/docker.sock:/var/run/docker.sock"; fi
        RUN_CMD="$RUN_CMD $ENVS $IMAGE"
        eval "$RUN_CMD"
        echo "Waiting for server to be ready..."
        HOST_PORT=$(echo "$PORTS" | grep -oE '^[0-9]+' | head -1)
        HOST_PORT="${HOST_PORT:-8080}"
        for i in $(seq 1 30); do
            if curl -sf "http://localhost:$HOST_PORT/api/health" &>/dev/null; then
                echo "Clawforce updated and running on http://localhost:$HOST_PORT"
                break
            fi
            if [ "$i" -eq 30 ]; then
                echo "Server not responding after 30s. Check logs: clawforce logs"
                exit 1
            fi
            sleep 1
        done
        ;;
    logs)
        $ENGINE logs -f "$CONTAINER"
        ;;
    status)
        $ENGINE ps -a --filter "name=^/${CONTAINER}$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
EOF
    chmod +x "$tmpfile"
    mv "$tmpfile" "$wrapper_path" 2>/dev/null || { rm -f "$tmpfile" 2>/dev/null; warn "Failed to install CLI wrapper."; return 1; }

    if command_exists clawforce; then
        success "CLI wrapper installed (run 'clawforce' to manage container)"
    else
        # $HOME/.local/bin is not in PATH — advise the user
        warn "'$install_dir' is not in your PATH."
        echo "  Add it by running:"
        echo ""
        if [ -f "$HOME/.zshrc" ]; then
            echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
        else
            echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
        fi
        echo ""
    fi
}

install_cli_wrapper

# ─────────────────────────────────────────────────────────────────────────────
# Run container
# ─────────────────────────────────────────────────────────────────────────────
info "Starting Clawforce on port $PORT..."

RUN_ARGS=(
    -d
    -p "$PORT:8080"
    -e "ADMIN_SETUP_USERNAME=$ADMIN_USER"
    -e "ADMIN_SETUP_PASSWORD=$ADMIN_PASS"
    -e "AGENT_IMAGE=$IMAGE"
    -e "AGENT_STORAGE_HOST_PATH=$DATA_DIR"
    -v "$DATA_DIR:/data"
    --name "$CONTAINER"
    --restart unless-stopped
)

if $PROCESS_RUNTIME; then
    info "Using process runtime (no container isolation for agents)"
    RUN_ARGS+=(-e "ADMIN_RUNTIME_BACKEND=process")
else
    info "Using container isolation for agents"
    if [ "$ENGINE" = "podman" ]; then
        SOCK_PATH="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
        RUN_ARGS+=(-v "$SOCK_PATH:/var/run/docker.sock")
    else
        RUN_ARGS+=(-v "/var/run/docker.sock:/var/run/docker.sock")
    fi
fi

engine_cmd run "${RUN_ARGS[@]}" "$IMAGE"

# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────
info "Waiting for server to be ready..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:$PORT/api/health" &>/dev/null; then
        break
    fi
    if [ "$i" -eq 30 ]; then
        warn "Server not responding after 30s"
        echo ""
        echo "Check logs with: $ENGINE logs $CONTAINER"
        exit 1
    fi
    sleep 1
done

# ─────────────────────────────────────────────────────────────────────────────
# Success
# ─────────────────────────────────────────────────────────────────────────────
echo ""
success "Clawforce is running!"
echo ""
echo "  ┌─────────────────────────────────────────────────────────────────┐"
echo "  │                                                                 │"
echo "  │   Dashboard:    $(printf '\033]8;;http://localhost:%s\033\\http://localhost:%s\033]8;;\033\\' "$PORT" "$PORT")                          │"
echo "  │   Username:     $ADMIN_USER                                     │"
echo "  │   Password:     $ADMIN_PASS                                     │"
echo "  │   Data:         $DATA_DIR                                       │"
echo "  │                                                                 │"
echo "  └─────────────────────────────────────────────────────────────────┘"
if [ "$ADMIN_PASS" = "admin" ]; then
    echo ""
    warn "Default password 'admin' is in use — change it immediately after first login."
fi
echo ""
echo "  Commands:"
echo "    Logs:           clawforce logs"
echo "    Stop:           clawforce stop"
echo "    Start:          clawforce start"
echo "    Status:         clawforce status"
echo "    Update:         clawforce update"
echo "    Uninstall:      curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash -s -- --uninstall"
echo ""
echo "  Documentation:    https://github.com/saolalab/clawforce"
echo ""
