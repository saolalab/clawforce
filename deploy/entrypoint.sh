#!/bin/sh
# All-in-one entrypoint: optional setup, then exec CMD.
# k8s runtime uses the same image (AGENT_IMAGE) for agent worker pods.

set -e

# Default credentials for first-run setup (override for production).
export ADMIN_SETUP_USERNAME="${ADMIN_SETUP_USERNAME:-admin}"
export ADMIN_SETUP_PASSWORD="${ADMIN_SETUP_PASSWORD:-admin}"

# Skip admin setup when running as an agent worker (same image, different role).
if [ -z "${AGENT_ROOT}" ] && [ -n "${ADMIN_SETUP_USERNAME}" ] && [ -n "${ADMIN_SETUP_PASSWORD}" ]; then
    export ADMIN_STORAGE_ROOT="${ADMIN_STORAGE_ROOT:-/data}"
    clawforce setup --data-dir "$ADMIN_STORAGE_ROOT" || true
fi

exec "$@"
