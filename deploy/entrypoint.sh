#!/bin/sh
# All-in-one entrypoint: optional setup, then exec CMD.
# Docker pool uses the same image (AGENT_IMAGE) for worker containers.

set -e

# Skip admin setup when running as an agent worker (same image, different role).
if [ -z "${AGENT_ROOT}" ] && [ -n "${ADMIN_SETUP_USERNAME}" ] && [ -n "${ADMIN_SETUP_PASSWORD}" ]; then
    export ADMIN_STORAGE_ROOT="${ADMIN_STORAGE_ROOT:-/data}"
    clawforce setup --data-dir "$ADMIN_STORAGE_ROOT" || true
fi

exec "$@"
