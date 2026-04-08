# Clawforce Makefile
#
# Development:   make dev        (or: make backend + make frontend in two terminals)
# Docs preview:  make docs       (VitePress at http://localhost:4173/clawforce/)
# Production:    make install && clawforce setup && clawforce serve
# k3s deploy:    make pod        (build + import into k3s + kubectl apply)
# Stop/cleanup:  make pod-stop   (removes all clawforce + agent pods)

# Kubernetes namespace
NAMESPACE ?= clawforce
# kubectl command (falls back to k3s kubectl)
KUBECTL ?= $(shell command -v kubectl >/dev/null 2>&1 && echo kubectl || echo /usr/local/bin/k3s kubectl)

.PHONY: install dev backend frontend docs docs-dev setup build test lint lint-fix format clean user-list user-create user-update user-set-password pod pod-nobuild pod-clean pod-logs pod-stop

# ─────────────────────────────────────────────────────────────────────────────
# Installation
# ─────────────────────────────────────────────────────────────────────────────

install:
	@echo "Installing Python dependencies..."
	uv sync --group dev
	@echo "Installing frontend dependencies..."
	cd clawforce-ui && npm install
	@echo ""
	@echo "Installation complete. Next steps:"
	@echo "  1. clawforce setup              # Create admin user"
	@echo "  2. clawforce serve              # Start server"

# ─────────────────────────────────────────────────────────────────────────────
# Development (hot-reload)
# ─────────────────────────────────────────────────────────────────────────────

dev:
	@echo "Starting development servers..."
	@echo "  Backend:  http://localhost:8080"
	@echo "  Frontend: http://localhost:5173"
	@echo ""
	@echo "Run in two terminals: make backend | make frontend"

backend:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m clawforce.cli serve --host 127.0.0.1 --port 8080 --reload

frontend:
	cd clawforce-ui && npm run dev

docs:
	npm run docs:build && npm run docs:preview

docs-dev:
	npm run docs:dev

# ─────────────────────────────────────────────────────────────────────────────
# Setup & Production
# ─────────────────────────────────────────────────────────────────────────────

setup:
	ADMIN_STORAGE_ROOT=$$(pwd)/data ADMIN_SETUP_USERNAME=admin ADMIN_SETUP_PASSWORD=admin uv run python -m clawforce.cli setup

user-list:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m clawforce.cli user list

# Create user: make user-create CREATE_USER=alice CREATE_PASS=secret
user-create:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m clawforce.cli user create $(CREATE_USER) --password $(CREATE_PASS)

# Update user: make user-update UPDATE_USER=alice UPDATE_PASS=newpass
user-update:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m clawforce.cli user update $(UPDATE_USER) --password $(UPDATE_PASS)

# Reset password: make user-set-password RESET_USER=admin
user-set-password:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m clawforce.cli user set-password $(RESET_USER)

serve:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m clawforce.cli serve --port 8080

# Build production frontend (outputs directly to clawforce/static/)
build:
	cd clawforce-ui && npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Testing & Quality
# ─────────────────────────────────────────────────────────────────────────────

test:
	uv run python -m pytest tests/ -v

lint:
	uv run ruff check .
	uv run ruff format --check .

lint-fix:
	uv run ruff check . --fix

format:
	uv run ruff format .

# ─────────────────────────────────────────────────────────────────────────────
# k3s / Kubernetes (local dev) — requires k3s, Rancher Desktop, or k3d
# ─────────────────────────────────────────────────────────────────────────────

pod:
	./scripts/dev.sh --logs

pod-nobuild:
	./scripts/dev.sh --no-build --logs

pod-clean:
	./scripts/dev.sh --clean --logs

pod-logs:
	$(KUBECTL) logs -f deployment/clawforce -n $(NAMESPACE)

pod-stop:
	@echo "Stopping and removing clawforce pods..."
	-@$(KUBECTL) delete pods -n $(NAMESPACE) -l app=clawbot-agent --grace-period=0 2>/dev/null || true
	-@$(KUBECTL) delete pods -n $(NAMESPACE) -l app=clawforce-oauth-cb --grace-period=0 2>/dev/null || true
	-@$(KUBECTL) scale deployment/clawforce --replicas=0 -n $(NAMESPACE) 2>/dev/null || true
	@echo "Done."

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
