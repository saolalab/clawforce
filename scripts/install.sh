#!/usr/bin/env bash
#
# Clawforce Installer — deploys on k3s (Kubernetes)
#
# Supported platforms:
#   Linux  — installs k3s natively
#   macOS  — guides through Rancher Desktop or k3d (k3s doesn't run natively)
#   Windows WSL2 — installs k3s inside WSL2 then exposes via localhost
#
# One-line install:
#   curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash
#
# Or with custom options:
#   curl -fsSL ... | bash -s -- --port 30080 --data /opt/clawforce-data
#
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
IMAGE="${CLAWFORCE_IMAGE:-ghcr.io/saolalab/clawforce:latest}"
NAMESPACE="${CLAWFORCE_NAMESPACE:-clawforce}"
PORT="${CLAWFORCE_PORT:-30080}"           # k3s NodePort
ADMIN_USER="${CLAWFORCE_ADMIN_USER:-admin}"
ADMIN_PASS="${CLAWFORCE_ADMIN_PASS:-admin}"
SKIP_K3S_INSTALL="${CLAWFORCE_SKIP_K3S:-false}"
PROCESS_RUNTIME="${CLAWFORCE_PROCESS_RUNTIME:-false}"

# ─────────────────────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────
show_help() {
    cat << EOF
Clawforce Installer  (Linux / macOS / Windows WSL2)

Usage: install.sh [OPTIONS]

Options:
  --port PORT           NodePort to expose (default: 30080)
  --data DIR            Host data directory
                          Linux/WSL2 default: /opt/clawforce-data
                          macOS default:      \$HOME/.clawforce-data
  --admin-user USER     Admin username (default: admin)
  --admin-pass PASS     Admin password (default: admin)
  --namespace NS        Kubernetes namespace (default: clawforce)
  --process-runtime     Use process runtime instead of k8s pod isolation
  --skip-k3s            Skip k3s/kubectl installation check
  --uninstall           Remove Clawforce deployment and optionally data
  -h, --help            Show this help message

Environment variables:
  CLAWFORCE_IMAGE       Container image (default: ghcr.io/saolalab/clawforce:latest)
  CLAWFORCE_PORT        NodePort to expose
  CLAWFORCE_DATA        Data directory path
  CLAWFORCE_ADMIN_USER  Admin username
  CLAWFORCE_ADMIN_PASS  Admin password
  CLAWFORCE_NAMESPACE   Kubernetes namespace

Platform notes:
  Linux       k3s is installed automatically if not present.
  macOS       k3s does not run natively. The script installs k3d via Homebrew
              (k3s in a Docker container) or guides through Rancher Desktop.
  Windows     Run this script inside WSL2. k3s is installed in WSL2 and
              the NodePort is accessible at localhost:<PORT> from Windows.
              For native Windows (no WSL2), use scripts/install.ps1 instead.

EOF
    exit 0
}

UNINSTALL=false
DATA_DIR="${CLAWFORCE_DATA:-}"    # resolved after OS detection

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)            PORT="$2"; shift 2 ;;
        --data)            DATA_DIR="$2"; shift 2 ;;
        --admin-user)      ADMIN_USER="$2"; shift 2 ;;
        --admin-pass)      ADMIN_PASS="$2"; shift 2 ;;
        --namespace)       NAMESPACE="$2"; shift 2 ;;
        --process-runtime) PROCESS_RUNTIME=true; shift ;;
        --skip-k3s)        SKIP_K3S_INSTALL=true; shift ;;
        --uninstall)       UNINSTALL=true; shift ;;
        -h|--help)         show_help ;;
        *)                 echo "Unknown option: $1"; show_help ;;
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

command_exists() { command -v "$1" &>/dev/null; }

# ─────────────────────────────────────────────────────────────────────────────
# OS / environment detection
# ─────────────────────────────────────────────────────────────────────────────
detect_os() {
    case "$(uname -s)" in
        Linux*)
            # Distinguish WSL2 from native Linux
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl2"
            else
                echo "linux"
            fi
            ;;
        Darwin*) echo "macos" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows-shell" ;;
        *) echo "unknown" ;;
    esac
}

detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64)  echo "amd64" ;;
        aarch64|arm64) echo "arm64" ;;
        armv7l)        echo "arm" ;;
        *)             echo "unknown" ;;
    esac
}

OS=$(detect_os)
ARCH=$(detect_arch)

# Resolve platform-appropriate default data directory
if [ -z "$DATA_DIR" ]; then
    case "$OS" in
        macos)          DATA_DIR="$HOME/.clawforce-data" ;;
        wsl2)           DATA_DIR="/opt/clawforce-data" ;;
        linux)          DATA_DIR="/opt/clawforce-data" ;;
        windows-shell)  DATA_DIR="$HOME/.clawforce-data" ;;
        *)              DATA_DIR="/opt/clawforce-data" ;;
    esac
fi

# kubectl wrapper: prefers kubectl, falls back to k3s kubectl
kubectl_cmd() {
    if command_exists kubectl; then
        kubectl "$@"
    elif [ -f /usr/local/bin/k3s ]; then
        /usr/local/bin/k3s kubectl "$@"
    else
        die "kubectl not found. Install k3s or kubectl first."
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Uninstall
# ─────────────────────────────────────────────────────────────────────────────
if $UNINSTALL; then
    info "Uninstalling Clawforce..."

    if ! kubectl_cmd cluster-info &>/dev/null 2>&1; then
        warn "No accessible k8s cluster — skipping resource deletion."
    else
        kubectl_cmd delete deployment clawforce -n "$NAMESPACE" 2>/dev/null || true
        kubectl_cmd delete pods -l app=clawbot-agent -n "$NAMESPACE" 2>/dev/null || true
        kubectl_cmd delete pods -l app=clawforce-oauth-cb -n "$NAMESPACE" 2>/dev/null || true
        kubectl_cmd delete service clawforce -n "$NAMESPACE" 2>/dev/null || true
        kubectl_cmd delete serviceaccount clawforce -n "$NAMESPACE" 2>/dev/null || true
        kubectl_cmd delete clusterrolebinding clawforce-pod-manager 2>/dev/null || true
        kubectl_cmd delete clusterrole clawforce-pod-manager 2>/dev/null || true
        kubectl_cmd delete namespace "$NAMESPACE" 2>/dev/null || true
        success "Kubernetes resources removed"
    fi

    if [ -d "$DATA_DIR" ]; then
        echo ""
        printf "Remove data directory %s? [y/N]: " "$DATA_DIR"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            sudo rm -rf "$DATA_DIR" 2>/dev/null || rm -rf "$DATA_DIR"
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
echo "  ║    Powered by k3s (Kubernetes)                       ║"
echo "  ║                                                      ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""
info "Platform: $OS ($ARCH)"

# ─────────────────────────────────────────────────────────────────────────────
# Platform-specific k3s/kubectl installation
# ─────────────────────────────────────────────────────────────────────────────

# ── Linux (native) ────────────────────────────────────────────────────────────
install_k3s_linux() {
    info "Installing k3s..."
    # K3S_INSTALL_SKIP_START is not used — let the official installer start k3s.
    curl -sfL https://get.k3s.io | sh -

    info "Waiting for k3s to start (up to 60s)..."
    local tries=0
    while ! /usr/local/bin/k3s kubectl get nodes &>/dev/null 2>&1; do
        tries=$((tries + 1))
        [ "$tries" -ge 30 ] && die "k3s did not start within 60s.\nCheck: sudo systemctl status k3s"
        sleep 2
    done
    success "k3s is running"

    # Give the current user a readable kubeconfig without sudo for every command.
    if [ -f /etc/rancher/k3s/k3s.yaml ]; then
        mkdir -p "$HOME/.kube"
        sudo cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
        sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config"
        chmod 600 "$HOME/.kube/config"
        success "kubeconfig written to $HOME/.kube/config"
    fi
}

# ── WSL2 ──────────────────────────────────────────────────────────────────────
# k3s runs fine inside WSL2; the NodePort is reachable from Windows via localhost.
install_k3s_wsl2() {
    info "Installing k3s inside WSL2..."

    # WSL2 uses a custom init — k3s installer handles this via openrc/s6 fallback.
    # We pin INSTALL_K3S_SKIP_SELINUX_RPM to avoid rpm errors on Ubuntu WSL images.
    curl -sfL https://get.k3s.io | INSTALL_K3S_SKIP_SELINUX_RPM=true sh -

    # k3s may not auto-start in WSL2 (no systemd by default on older WSL).
    # Attempt systemd first, then direct start.
    if systemctl is-active k3s &>/dev/null 2>&1; then
        success "k3s started via systemd"
    elif command_exists systemctl && systemctl start k3s 2>/dev/null; then
        success "k3s started via systemctl"
    else
        info "Starting k3s directly (non-systemd WSL2)..."
        # Run in background; stdout/stderr to log file so installer continues.
        sudo /usr/local/bin/k3s server \
            --disable traefik \
            --write-kubeconfig-mode 644 \
            > /tmp/k3s.log 2>&1 &
        disown
    fi

    info "Waiting for k3s to start (up to 60s)..."
    local tries=0
    while ! /usr/local/bin/k3s kubectl get nodes &>/dev/null 2>&1; do
        tries=$((tries + 1))
        [ "$tries" -ge 30 ] && die "k3s did not start within 60s.\nCheck: cat /tmp/k3s.log"
        sleep 2
    done
    success "k3s is running inside WSL2"
    warn "The NodePort will be accessible at localhost:${PORT} from Windows."

    if [ -f /etc/rancher/k3s/k3s.yaml ]; then
        mkdir -p "$HOME/.kube"
        sudo cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
        sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config"
        chmod 600 "$HOME/.kube/config"
        success "kubeconfig written to $HOME/.kube/config"
    fi
}

# ── macOS ─────────────────────────────────────────────────────────────────────
# k3s does not run natively on macOS (Linux kernel required).
# We support two paths:
#   1. k3d  — k3s packaged inside a Docker/OrbStack container (recommended for CI / devs)
#   2. Rancher Desktop — GUI app that ships a k3s VM; kubectl is auto-configured
install_k3s_macos() {
    echo ""
    echo "  k3s requires a Linux kernel and cannot run natively on macOS."
    echo "  Choose an installation method:"
    echo ""
    echo "  [1] k3d (k3s in Docker) — lightweight, great for development"
    echo "      Requires: Docker Desktop, OrbStack, or Colima"
    echo ""
    echo "  [2] Rancher Desktop — full GUI app with built-in k3s VM"
    echo "      Download: https://rancherdesktop.io"
    echo ""
    printf "  Your choice [1/2] (default: 1): "
    read -r choice
    choice="${choice:-1}"

    case "$choice" in
        1) install_k3d_macos ;;
        2) guide_rancher_desktop_macos ;;
        *) die "Invalid choice. Run the script again." ;;
    esac
}

install_k3d_macos() {
    # Ensure a container runtime is available
    if ! command_exists docker && ! command_exists nerdctl; then
        echo ""
        error "No container runtime found. k3d needs Docker, OrbStack, or Colima."
        echo ""
        echo "  Quick options:"
        echo "    OrbStack (fast, lightweight): https://orbstack.dev"
        echo "    Docker Desktop:              https://docs.docker.com/desktop/install/mac-install/"
        echo "    Colima (CLI, free):          brew install colima && colima start"
        echo ""
        die "Install a container runtime then re-run this script."
    fi

    if command_exists k3d; then
        success "k3d is already installed"
    else
        if command_exists brew; then
            info "Installing k3d via Homebrew..."
            brew install k3d
            success "k3d installed"
        else
            info "Installing k3d via official installer..."
            curl -sfL https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
            success "k3d installed"
        fi
    fi

    # Create or reuse a k3d cluster named "clawforce"
    if k3d cluster list 2>/dev/null | grep -q "^clawforce"; then
        info "k3d cluster 'clawforce' already exists — reusing it"
        k3d cluster start clawforce 2>/dev/null || true
    else
        info "Creating k3d cluster 'clawforce' (NodePort ${PORT} → 30080)..."
        k3d cluster create clawforce \
            --port "${PORT}:30080@loadbalancer" \
            --agents 1
        success "k3d cluster 'clawforce' created"
    fi

    # k3d writes kubeconfig automatically
    k3d kubeconfig merge clawforce --kubeconfig-merge-default --kubeconfig-switch-context
    success "kubeconfig updated (context: k3d-clawforce)"

    # On macOS with k3d the NodePort is served via the load-balancer on 127.0.0.1:PORT
    warn "Access Clawforce at http://localhost:${PORT} (k3d load-balancer)"
}

guide_rancher_desktop_macos() {
    echo ""
    if command_exists kubectl && kubectl_cmd get nodes &>/dev/null 2>&1; then
        success "Rancher Desktop is already running — proceeding with deployment."
        return 0
    fi

    echo "  Please install and start Rancher Desktop:"
    echo ""
    if command_exists brew; then
        echo "    brew install --cask rancher"
        echo "    # Then open Rancher Desktop from Applications and wait for it to start."
    else
        echo "    Download from: https://rancherdesktop.io"
    fi
    echo ""
    echo "  After Rancher Desktop is running, re-run this installer:"
    echo "    curl -fsSL https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh | bash"
    echo ""
    exit 0
}

# ── Windows (Git Bash / MSYS2 — not WSL2) ────────────────────────────────────
guide_windows_shell() {
    echo ""
    warn "You appear to be running in Git Bash or MSYS2 on Windows (not WSL2)."
    echo ""
    echo "  Recommended installation paths for Windows:"
    echo ""
    echo "  [A] WSL2 (recommended)"
    echo "      Install WSL2:  https://learn.microsoft.com/windows/wsl/install"
    echo "      Then run this script inside your WSL2 terminal."
    echo ""
    echo "  [B] Native PowerShell installer"
    echo "      Run in an elevated PowerShell (Administrator):"
    echo "      irm https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.ps1 | iex"
    echo ""
    echo "  [C] Rancher Desktop for Windows (GUI)"
    echo "      https://rancherdesktop.io — ships kubectl + k3s VM"
    echo "      After installing, kubectl will be in PATH; re-run this script."
    echo ""
    printf "  Continue anyway (kubectl must already be in PATH)? [y/N]: "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 0
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Main k3s / kubectl check + install
# ─────────────────────────────────────────────────────────────────────────────
check_and_install_k3s() {
    if $SKIP_K3S_INSTALL; then
        info "Skipping k3s check (--skip-k3s)"
        return 0
    fi

    # Already working?
    if kubectl_cmd get nodes &>/dev/null 2>&1; then
        success "k8s cluster is reachable — skipping installation"
        return 0
    fi

    case "$OS" in
        linux)
            if [ -f /usr/local/bin/k3s ]; then
                # k3s binary present but cluster unreachable — try to start it
                info "k3s binary found but cluster is not responding. Starting k3s..."
                sudo systemctl start k3s 2>/dev/null || \
                    sudo /usr/local/bin/k3s server --disable traefik > /tmp/k3s.log 2>&1 &
                disown 2>/dev/null || true
                sleep 5
                if kubectl_cmd get nodes &>/dev/null 2>&1; then
                    success "k3s started"
                    return 0
                fi
            fi
            warn "k3s is not installed."
            printf "Install k3s now? [Y/n]: "
            read -r response
            if [[ ! "$response" =~ ^[Nn]$ ]]; then
                install_k3s_linux
            else
                die "k3s is required. Install from https://k3s.io"
            fi
            ;;

        wsl2)
            if [ -f /usr/local/bin/k3s ]; then
                info "k3s binary found. Starting k3s in WSL2..."
                # Try systemd, fall back to direct start
                sudo systemctl start k3s 2>/dev/null || \
                    { sudo /usr/local/bin/k3s server --disable traefik \
                        > /tmp/k3s.log 2>&1 & disown 2>/dev/null || true; }
                sleep 5
                if kubectl_cmd get nodes &>/dev/null 2>&1; then
                    success "k3s started"
                    return 0
                fi
            fi
            warn "k3s is not installed in this WSL2 instance."
            printf "Install k3s now? [Y/n]: "
            read -r response
            if [[ ! "$response" =~ ^[Nn]$ ]]; then
                install_k3s_wsl2
            else
                die "k3s is required. Install from https://k3s.io"
            fi
            ;;

        macos)
            install_k3s_macos
            ;;

        windows-shell)
            guide_windows_shell
            ;;

        *)
            die "Unsupported OS '${OS}'. Please install k3s manually: https://k3s.io"
            ;;
    esac
}

check_and_install_k3s

# Final sanity check
kubectl_cmd cluster-info &>/dev/null || \
    die "k8s cluster is still not reachable after installation. Check k3s status."

# ─────────────────────────────────────────────────────────────────────────────
# Data directory
# ─────────────────────────────────────────────────────────────────────────────
info "Setting up data directory: $DATA_DIR"
if [[ "$OS" == "linux" || "$OS" == "wsl2" ]]; then
    sudo mkdir -p "$DATA_DIR"
    sudo chown "$(id -u):$(id -g)" "$DATA_DIR" 2>/dev/null || true
else
    mkdir -p "$DATA_DIR"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Apply Kubernetes manifests
# ─────────────────────────────────────────────────────────────────────────────
info "Creating namespace and RBAC..."
kubectl_cmd apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $NAMESPACE
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: clawforce
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: clawforce-pod-manager
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log", "pods/exec", "namespaces"]
    verbs: ["create", "delete", "get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: clawforce-pod-manager
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: clawforce-pod-manager
subjects:
  - kind: ServiceAccount
    name: clawforce
    namespace: $NAMESPACE
EOF
success "Namespace and RBAC configured"

if $PROCESS_RUNTIME; then
    RUNTIME_BACKEND="process"
    info "Using process runtime (no pod isolation for agents)"
else
    RUNTIME_BACKEND="k8s"
    info "Using k8s pod isolation for agents"
fi

# Pre-pull image into k3s containerd (Linux / WSL2 only; not applicable on k3d)
if command_exists k3s && [[ "$OS" == "linux" || "$OS" == "wsl2" ]]; then
    info "Pre-pulling image into k3s containerd: $IMAGE"
    sudo k3s crictl pull "$IMAGE" 2>/dev/null || \
        warn "Could not pre-pull image (will pull on pod start)"
fi

info "Deploying Clawforce..."
kubectl_cmd apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: clawforce
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: clawforce
  template:
    metadata:
      labels:
        app: clawforce
    spec:
      serviceAccountName: clawforce
      containers:
        - name: clawforce
          image: $IMAGE
          imagePullPolicy: Always
          ports:
            - containerPort: 8080
          env:
            - name: ADMIN_RUNTIME_BACKEND
              value: "$RUNTIME_BACKEND"
            - name: K8S_NAMESPACE
              value: "$NAMESPACE"
            - name: ADMIN_STORAGE_ROOT
              value: "/data"
            - name: ADMIN_PUBLIC_URL
              value: "http://clawforce.$NAMESPACE.svc.cluster.local:8080"
            - name: AGENT_STORAGE_HOST_PATH
              value: "$DATA_DIR"
            - name: AGENT_IMAGE
              value: "$IMAGE"
            - name: ADMIN_SETUP_USERNAME
              value: "$ADMIN_USER"
            - name: ADMIN_SETUP_PASSWORD
              value: "$ADMIN_PASS"
          volumeMounts:
            - name: data
              mountPath: /data
          livenessProbe:
            httpGet:
              path: /api/health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 30
            timeoutSeconds: 5
          readinessProbe:
            httpGet:
              path: /api/health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 3
      volumes:
        - name: data
          hostPath:
            path: $DATA_DIR
            type: DirectoryOrCreate
---
apiVersion: v1
kind: Service
metadata:
  name: clawforce
  namespace: $NAMESPACE
spec:
  selector:
    app: clawforce
  ports:
    - name: http
      port: 8080
      targetPort: 8080
      nodePort: $PORT
  type: NodePort
EOF
success "Deployment and Service applied"

# ─────────────────────────────────────────────────────────────────────────────
# Install CLI wrapper
# ─────────────────────────────────────────────────────────────────────────────
install_cli_wrapper() {
    info "Installing 'clawforce' CLI wrapper..."

    cd "${TMPDIR:-/tmp}" 2>/dev/null || cd /tmp 2>/dev/null || true

    local install_dir=""
    for _candidate in "$HOME/.local/bin" "$HOME/bin" "$HOME/.bin"; do
        if mkdir -p "$_candidate" 2>/dev/null; then
            install_dir="$_candidate"
            break
        fi
    done
    if [ -z "$install_dir" ]; then
        warn "Could not find a writable bin directory — skipping CLI wrapper."
        return 1
    fi

    local wrapper_path="$install_dir/clawforce"
    local tmpfile
    tmpfile="$(mktemp)" || { warn "mktemp failed — skipping CLI wrapper."; return 1; }

    cat > "$tmpfile" << 'WRAPPER_EOF'
#!/usr/bin/env bash
# clawforce — Manage the Clawforce k3s deployment

NAMESPACE="${CLAWFORCE_NAMESPACE:-clawforce}"

kubectl_cmd() {
    if command -v kubectl &>/dev/null; then
        kubectl "$@"
    elif [ -f /usr/local/bin/k3s ]; then
        /usr/local/bin/k3s kubectl "$@"
    else
        echo "Error: kubectl not found in PATH" >&2
        exit 1
    fi
}

show_help() {
    echo "Usage: clawforce <command>"
    echo ""
    echo "Commands:"
    echo "  start     Scale up the Clawforce deployment (replicas=1)"
    echo "  stop      Scale down the Clawforce deployment (replicas=0)"
    echo "  restart   Restart the Clawforce pods"
    echo "  update    Pull the latest image and restart"
    echo "  logs      Stream pod logs"
    echo "  status    Show pod and agent status"
    echo "  shell     Open a shell in the Clawforce pod"
    echo ""
    echo "Environment:"
    echo "  CLAWFORCE_NAMESPACE   Kubernetes namespace (default: clawforce)"
}

[ $# -eq 0 ] && { show_help; exit 1; }

case "$1" in
    start)
        echo "Starting Clawforce..."
        kubectl_cmd scale deployment/clawforce --replicas=1 -n "$NAMESPACE"
        ;;
    stop)
        echo "Stopping Clawforce..."
        kubectl_cmd scale deployment/clawforce --replicas=0 -n "$NAMESPACE"
        ;;
    restart)
        echo "Restarting Clawforce..."
        kubectl_cmd rollout restart deployment/clawforce -n "$NAMESPACE"
        kubectl_cmd rollout status deployment/clawforce -n "$NAMESPACE" --timeout=60s
        ;;
    update)
        echo "Updating Clawforce..."
        IMAGE=$(kubectl_cmd get deployment/clawforce -n "$NAMESPACE" \
            -o jsonpath='{.spec.template.spec.containers[0].image}')
        echo "Pulling $IMAGE..."
        command -v k3s &>/dev/null && sudo k3s crictl pull "$IMAGE" 2>/dev/null || true
        kubectl_cmd rollout restart deployment/clawforce -n "$NAMESPACE"
        kubectl_cmd rollout status deployment/clawforce -n "$NAMESPACE" --timeout=120s
        NODE_PORT=$(kubectl_cmd get service/clawforce -n "$NAMESPACE" \
            -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30080")
        echo "Clawforce updated and running on http://localhost:${NODE_PORT}"
        ;;
    logs)
        kubectl_cmd logs -f deployment/clawforce -n "$NAMESPACE"
        ;;
    status)
        echo "=== Clawforce pod ==="
        kubectl_cmd get pods -n "$NAMESPACE" -l app=clawforce
        echo ""
        echo "=== Agent pods ==="
        kubectl_cmd get pods -n "$NAMESPACE" -l app=clawbot-agent 2>/dev/null || echo "(none)"
        ;;
    shell)
        POD=$(kubectl_cmd get pods -n "$NAMESPACE" -l app=clawforce \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        [ -z "$POD" ] && { echo "No Clawforce pod found" >&2; exit 1; }
        kubectl_cmd exec -it "$POD" -n "$NAMESPACE" -- /bin/bash
        ;;
    *)
        echo "Unknown command: $1" >&2
        show_help
        exit 1
        ;;
esac
WRAPPER_EOF

    chmod +x "$tmpfile"
    mv "$tmpfile" "$wrapper_path" 2>/dev/null || {
        rm -f "$tmpfile" 2>/dev/null
        warn "Failed to move wrapper to $wrapper_path — skipping."
        return 1
    }

    if command_exists clawforce; then
        success "CLI wrapper installed at $wrapper_path"
    else
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
# Wait for deployment
# ─────────────────────────────────────────────────────────────────────────────
info "Waiting for Clawforce to be ready..."
kubectl_cmd rollout status deployment/clawforce -n "$NAMESPACE" --timeout=120s || \
    warn "Rollout not complete within 120s — check: kubectl logs deployment/clawforce -n $NAMESPACE"

# Health check
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${PORT}/api/health" &>/dev/null; then
        break
    fi
    if [ "$i" -eq 30 ]; then
        warn "Server not responding on port $PORT after 30s"
        echo "  Logs: kubectl logs deployment/clawforce -n $NAMESPACE"
        break
    fi
    sleep 1
done

# ─────────────────────────────────────────────────────────────────────────────
# Success
# ─────────────────────────────────────────────────────────────────────────────
echo ""
success "Clawforce is running!"
echo ""
echo "  ┌────────────────────────────────────────────────────────────────┐"
echo "  │                                                                │"
printf "  │   Dashboard:  http://localhost:%-5s                          │\n" "$PORT"
printf "  │   Username:   %-48s│\n" "$ADMIN_USER"
printf "  │   Password:   %-48s│\n" "$ADMIN_PASS"
printf "  │   Data:       %-48s│\n" "$DATA_DIR"
printf "  │   Namespace:  %-48s│\n" "$NAMESPACE"
echo "  │                                                                │"
echo "  └────────────────────────────────────────────────────────────────┘"
if [ "$ADMIN_PASS" = "admin" ]; then
    echo ""
    warn "Default password 'admin' is in use — change it after first login."
fi
echo ""
echo "  Commands:"
echo "    clawforce logs     — stream pod logs"
echo "    clawforce stop     — scale to 0 replicas"
echo "    clawforce start    — scale to 1 replica"
echo "    clawforce status   — show pod status"
echo "    clawforce update   — pull latest image and restart"
echo ""
UNINSTALL_URL="https://raw.githubusercontent.com/saolalab/clawforce/main/scripts/install.sh"
echo "  Uninstall:"
echo "    curl -fsSL $UNINSTALL_URL | bash -s -- --uninstall"
echo ""
echo "  kubectl shortcuts:"
echo "    kubectl get pods -n $NAMESPACE"
echo "    kubectl logs -f deployment/clawforce -n $NAMESPACE"
echo ""
echo "  Documentation: https://github.com/saolalab/clawforce"
echo ""
