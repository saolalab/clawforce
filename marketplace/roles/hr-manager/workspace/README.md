# Workspace

This directory is the **runtime workspace** for the agent: memory, generated files, and collaboration data.

- `.agents/memory/MEMORY.md` — long-term facts
- `.agents/memory/HISTORY.md` — event log (grep-searchable)
- `.agents/HEARTBEAT.md` — periodic tasks (checked every 30 min)

Character setup (AGENTS, TOOLS, skills) lives in the profile and is read-only for the agent.
