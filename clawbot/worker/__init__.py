"""Agent worker: standalone process for local/docker pool backends.

Structure:
  context.py    - WorkerContext dataclass (runtime component bundle)
  resolve.py    - resolve_agent_root() from environment
  provision.py  - provision_agent_root() directory layout
  runtime.py    - create_worker_context() wires all components
  handlers/     - admin protocol handlers
    schema.py   - typed request/response models for the wire protocol
    admin.py    - handler logic + dispatch()
  lifespan.py   - run_worker() lifecycle (boot → run → shutdown)
  app.py        - main() entry point
"""
