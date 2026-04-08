#!/usr/bin/env bash
# Integration test: build image, import into k3s, run onboard + status as a k8s Job.
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

IMAGE_NAME="clawbot-test:local"
NAMESPACE="${TEST_NAMESPACE:-clawforce-test}"
JOB_ONBOARD="clawbot-test-onboard"
JOB_STATUS="clawbot-test-status"

kubectl_cmd() {
    if command -v kubectl &>/dev/null; then
        kubectl "$@"
    elif [ -f /usr/local/bin/k3s ]; then
        /usr/local/bin/k3s kubectl "$@"
    else
        echo "kubectl not found"; exit 1
    fi
}

# ── Build ─────────────────────────────────────────────────────────────────────
echo "=== Building image ==="
if command -v nerdctl &>/dev/null; then
    BUILDER="nerdctl"
elif command -v docker &>/dev/null; then
    BUILDER="docker"
else
    echo "No image builder found (need nerdctl or docker)"; exit 1
fi
$BUILDER build -t "$IMAGE_NAME" -f deploy/Dockerfile .

# Import into k3s containerd (skip if nerdctl — shares containerd)
if [ "$BUILDER" = "docker" ] && command -v k3s &>/dev/null; then
    echo "=== Importing image into k3s ==="
    docker save "$IMAGE_NAME" | sudo k3s ctr images import -
fi

# ── Namespace ─────────────────────────────────────────────────────────────────
kubectl_cmd create namespace "$NAMESPACE" 2>/dev/null || true

# ── Cleanup helper ────────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "=== Cleanup ==="
    kubectl_cmd delete job "$JOB_ONBOARD" -n "$NAMESPACE" 2>/dev/null || true
    kubectl_cmd delete job "$JOB_STATUS"  -n "$NAMESPACE" 2>/dev/null || true
    kubectl_cmd delete namespace "$NAMESPACE" 2>/dev/null || true
}
trap cleanup EXIT

# ── Run 'clawbot onboard' as a Job ───────────────────────────────────────────
echo ""
echo "=== Running 'clawbot onboard' as a k8s Job ==="
kubectl_cmd apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: $JOB_ONBOARD
  namespace: $NAMESPACE
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: test
          image: $IMAGE_NAME
          imagePullPolicy: Never
          command: ["clawbot", "onboard"]
EOF

kubectl_cmd wait --for=condition=complete job/"$JOB_ONBOARD" -n "$NAMESPACE" --timeout=60s

# ── Run 'clawbot status' as a Job and capture logs ───────────────────────────
echo ""
echo "=== Running 'clawbot status' as a k8s Job ==="
kubectl_cmd apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: $JOB_STATUS
  namespace: $NAMESPACE
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: test
          image: $IMAGE_NAME
          imagePullPolicy: Never
          command: ["clawbot", "status"]
EOF

kubectl_cmd wait --for=condition=complete job/"$JOB_STATUS" -n "$NAMESPACE" --timeout=60s

STATUS_POD=$(kubectl_cmd get pods -n "$NAMESPACE" -l job-name="$JOB_STATUS" \
    -o jsonpath='{.items[0].metadata.name}')
STATUS_OUTPUT=$(kubectl_cmd logs "$STATUS_POD" -n "$NAMESPACE" 2>&1) || true
echo "$STATUS_OUTPUT"

# ── Validate output ───────────────────────────────────────────────────────────
echo ""
echo "=== Validating output ==="
PASS=true

check() {
    if echo "$STATUS_OUTPUT" | grep -q "$1"; then
        echo "  PASS: found '$1'"
    else
        echo "  FAIL: missing '$1'"
        PASS=false
    fi
}

check "clawbot Status"
check "Config:"
check "Workspace:"
check "Model:"
check "OpenRouter API:"
check "Anthropic API:"
check "OpenAI API:"

echo ""
if $PASS; then
    echo "=== All checks passed ==="
else
    echo "=== Some checks FAILED ==="
    exit 1
fi
