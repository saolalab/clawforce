#!/usr/bin/env bash
#
# Local k3s dev workflow: build image, import into k3s, apply manifests, run.
#
# Usage:
#   ./scripts/dev.sh              # full rebuild + deploy
#   ./scripts/dev.sh --no-build   # skip build, restart pod only
#   ./scripts/dev.sh --clean      # wipe data + redeploy
#   ./scripts/dev.sh --logs       # tail logs after deploying
#
set -euo pipefail

# ── Config (override via env) ────────────────────────────────────────────────
IMAGE="${IMAGE:-clawforce:dev}"
CONTAINER="${CONTAINER:-clawforce}"     # deployment name
NAMESPACE="${NAMESPACE:-clawforce}"
DATA_DIR="${DATA_DIR:-./data}"
PORT="${PORT:-30080}"                   # k3s NodePort
ADMIN_USER="${ADMIN_SETUP_USERNAME:-admin}"
ADMIN_PASS="${ADMIN_SETUP_PASSWORD:-admin}"
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
      echo "  --no-build   Skip image build (reuse existing image)"
      echo "  --clean      Remove data directory (fresh start)"
      echo "  --logs       Tail pod logs after deploying"
      echo ""
      echo "Environment overrides:"
      echo "  IMAGE=...              Image name  (default: clawforce:dev)"
      echo "  PORT=...               NodePort     (default: 30080)"
      echo "  ADMIN_JWT_SECRET=...   JWT secret  (stable dev default)"
      echo "  PROCESS_POOL=true      Use process pool instead of k8s pod isolation"
      echo "  NAMESPACE=...          k8s namespace (default: clawforce)"
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

kubectl_cmd() {
    if command -v kubectl &>/dev/null; then
        kubectl "$@"
    elif [ -f /usr/local/bin/k3s ]; then
        /usr/local/bin/k3s kubectl "$@"
    else
        echo "Error: kubectl not found in PATH"
        exit 1
    fi
}

# ── Pre-flight: k3s / kubectl ─────────────────────────────────────────────────
if ! kubectl_cmd cluster-info &>/dev/null; then
    warn "k3s cluster not reachable. Please start k3s:"
    echo "  Linux: sudo systemctl start k3s"
    echo "  macOS: start Rancher Desktop or run: k3d cluster create"
    exit 1
fi
ok "k3s cluster is reachable"

# ── Resolve DATA_DIR to absolute path ─────────────────────────────────────────
DATA_DIR="$(cd "$PROJECT_ROOT" && mkdir -p "$DATA_DIR" && cd "$DATA_DIR" && pwd)"

# ── Optional: wipe data directory ─────────────────────────────────────────────
if $DO_CLEAN_DATA; then
    warn "Removing data directory $DATA_DIR ..."
    rm -rf "$DATA_DIR"
    mkdir -p "$DATA_DIR"
    ok "Data directory wiped"
fi

# ── Build ─────────────────────────────────────────────────────────────────────
if $DO_BUILD; then
    # Detect image builder: nerdctl (Rancher Desktop) > docker
    if command -v nerdctl &>/dev/null; then
        BUILDER="nerdctl"
    elif command -v docker &>/dev/null; then
        BUILDER="docker"
    else
        warn "Neither nerdctl nor docker found. Install one to build images."
        exit 1
    fi

    info "Building $IMAGE with $BUILDER ..."
    $BUILDER build -t "$IMAGE" -f "$PROJECT_ROOT/deploy/Dockerfile" "$PROJECT_ROOT"
    ok "Image built: $IMAGE"

    # Import image into k3s containerd so pods can use it
    info "Importing $IMAGE into k3s containerd ..."
    if command -v nerdctl &>/dev/null; then
        # Rancher Desktop: nerdctl images are already in containerd used by k3s
        ok "Image already in k3s containerd (nerdctl shares the same containerd)"
    elif command -v docker &>/dev/null && command -v k3s &>/dev/null; then
        docker save "$IMAGE" | sudo k3s ctr images import -
        ok "Image imported into k3s"
    elif command -v k3d &>/dev/null; then
        k3d image import "$IMAGE"
        ok "Image imported via k3d"
    else
        warn "Could not import image into k3s containerd automatically."
        warn "You may need to run: docker save $IMAGE | sudo k3s ctr images import -"
    fi
else
    info "Skipping build (--no-build)"
fi

# ── Ensure namespace and RBAC ─────────────────────────────────────────────────
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
ok "Namespace and RBAC ready"

# ── Stop agent worker pods ─────────────────────────────────────────────────────
AGENT_PODS=$(kubectl_cmd get pods -n "$NAMESPACE" -l app=clawbot-agent \
    -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)
if [ -n "$AGENT_PODS" ]; then
    info "Removing agent worker pods ..."
    kubectl_cmd delete pods -n "$NAMESPACE" -l app=clawbot-agent --grace-period=0 2>/dev/null || true
    ok "Agent pods removed"
fi

# ── Determine runtime backend ─────────────────────────────────────────────────
if [ "${PROCESS_POOL:-false}" = "true" ]; then
    info "Using process pool (no pod isolation for agents)"
    RUNTIME_BACKEND="process"
else
    info "Using k8s pod isolation (one pod per agent)"
    RUNTIME_BACKEND="k8s"
fi

# Use Never pull policy for locally built images
IMAGE_PULL_POLICY="Never"

# ── Deploy ────────────────────────────────────────────────────────────────────
info "Deploying $CONTAINER on NodePort $PORT ..."

kubectl_cmd apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $CONTAINER
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: $CONTAINER
  template:
    metadata:
      labels:
        app: $CONTAINER
    spec:
      serviceAccountName: clawforce
      containers:
        - name: $CONTAINER
          image: $IMAGE
          imagePullPolicy: $IMAGE_PULL_POLICY
          ports:
            - containerPort: 8080
          env:
            - name: ADMIN_SETUP_USERNAME
              value: "$ADMIN_USER"
            - name: ADMIN_SETUP_PASSWORD
              value: "$ADMIN_PASS"
            - name: ADMIN_JWT_SECRET
              value: "$JWT_SECRET"
            - name: ADMIN_RUNTIME_BACKEND
              value: "$RUNTIME_BACKEND"
            - name: K8S_NAMESPACE
              value: "$NAMESPACE"
            - name: ADMIN_STORAGE_ROOT
              value: "/data"
            - name: ADMIN_PUBLIC_URL
              value: "http://clawforce.$NAMESPACE.svc.cluster.local:8080"
            - name: AGENT_IMAGE
              value: "$IMAGE"
            - name: AGENT_IMAGE_PULL_POLICY
              value: "$IMAGE_PULL_POLICY"
            - name: AGENT_STORAGE_HOST_PATH
              value: "$DATA_DIR"
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          hostPath:
            path: $DATA_DIR
            type: DirectoryOrCreate
---
apiVersion: v1
kind: Service
metadata:
  name: $CONTAINER
  namespace: $NAMESPACE
spec:
  selector:
    app: $CONTAINER
  ports:
    - name: http
      port: 8080
      targetPort: 8080
      nodePort: $PORT
  type: NodePort
EOF

# ── Restart to pick up new image ──────────────────────────────────────────────
kubectl_cmd rollout restart deployment/"$CONTAINER" -n "$NAMESPACE"

# ── Health check ──────────────────────────────────────────────────────────────
info "Waiting for server to be ready ..."
kubectl_cmd rollout status deployment/"$CONTAINER" -n "$NAMESPACE" --timeout=90s || \
    warn "Deployment not ready within 90s"

for i in $(seq 1 20); do
    if curl -sf "http://localhost:$PORT/api/health" &>/dev/null; then
        ok "Server is up at http://localhost:$PORT"
        break
    fi
    if [ "$i" -eq 20 ]; then
        warn "Server not responding after 20s — check: kubectl logs deployment/$CONTAINER -n $NAMESPACE"
    fi
    sleep 1
done

# ── Optional: tail logs ───────────────────────────────────────────────────────
if $DO_LOGS; then
    echo ""
    info "Tailing logs (Ctrl+C to stop) ..."
    kubectl_cmd logs -f deployment/"$CONTAINER" -n "$NAMESPACE"
fi
