# Tools

Tool parameters are provided via function calling — refer to each tool's schema for full details.
This document covers usage notes and conventions that go beyond the schema.

## File Operations

`read_file`, `write_file`, `edit_file`, `list_dir`, `workspace_tree`

- Paths are relative to your workspace unless an absolute path is given.
- `write_file` creates parent directories automatically.
- `edit_file` requires an exact match of `old_text` in the file.
- **Workspace overview**: Use `workspace_tree` for a hierarchical view instead of repeated `list_dir`. Prefer it when exploring structure.
- **Folder strategy**: Organize files into folders (e.g. `docs/`, `projects/`, `outputs/`) per `workspace/WORKSPACE_LAYOUT.md`. Avoid dumping files in the root.

## Shell (`exec`)

- Commands have a configurable timeout (default 60s).
- Dangerous commands are blocked (rm -rf /, format, dd, shutdown, etc.).
- Output is truncated at 10,000 characters.
- When `restrictToWorkspace` is enabled, paths outside the workspace are blocked.

## Web

`web_search`, `web_fetch`

- `web_search` uses Brave Search or SerpAPI depending on config.
- `web_fetch` extracts readable content from a URL (markdown or plain text, max 50k chars).
- SSRF protection is enabled by default (private/local URLs are blocked).

## Message (`message`)

Send a message to the user on their chat channel. Only use this when you need to push a message to a specific channel (e.g. WhatsApp, Telegram). For normal conversation, just respond with text directly.

## Background Tasks (`spawn`)

Spawn a subagent to handle a task in the background. Use for complex or time-consuming tasks that can run independently.

## Running installed software (via `spawn`) — **preferred for code**

**Prefer coding tools** over writing code manually. Installed catalog software (Claude Code, Gemini CLI, Codex CLI) is run by the subagent via `software_exec`. Use the **spawn** tool with a clear task (e.g. "Use software_exec with backend_key claude-code and task: Implement X in file Y"). Do not claim you cannot run these — use them for code generation, refactoring, and implementation.

## Git and GitHub

You have **git** and **github** skills. Use `git` for clone, pull, branch, commit, push. Use `gh` for PRs, issues, CI. When tasks require "pull → implement → commit → PR → report", follow that workflow and report via `add_task_comment` or `add_plan_artifact` per the task's Output section.

## Scheduled Jobs (`cron`)

Use the `cron` tool directly (not via shell) to schedule reminders or recurring tasks.

### Actions

- `add` — create a new job
- `list` — list all scheduled jobs
- `remove` — remove a job by ID

### Schedule types

| Type | Parameters | Behavior |
|------|-----------|----------|
| Interval | `every_seconds` | Repeats at fixed interval |
| Cron | `cron_expr`, optional `tz` | Standard cron expression |
| One-time | `at` (ISO datetime) | Runs once then auto-deletes |

### Examples

```
cron(action="add", message="Time to take a break!", every_seconds=1200)
cron(action="add", message="Morning standup", cron_expr="0 9 * * 1-5", tz="America/Vancouver")
cron(action="add", message="Remind me about the meeting", at="2026-02-21T15:00:00")
cron(action="list")
cron(action="remove", job_id="abc123")
```

Jobs are stored in `profiles/crons/jobs.json` and managed by the cron service.

## Heartbeat

The agent periodically checks `workspace/.agents/HEARTBEAT.md`. If it contains tasks, the agent wakes up and executes them. Use file operations to manage heartbeat tasks.

## Agent discovery (peers)

When the user asks about your peers, teammates, or who other agents are, use `a2a_discover` to list them and respond conversationally. Do NOT create plans, list plans, or use `list_plan_assignees` for such questions — those are for task assignment only.

## Planning and Coordination

Plan lifecycle has two phases. Do NOT call `create_plan` until the user confirms the proposal.

### Task template (required for create_plan_task)

Every task description MUST use: ## Context, ## Requirements, ## Definition of Done, ## Output. For code tasks, include workflow (pull → implement → commit → PR → report) and Output (add_task_comment, add_plan_artifact).

### Phase 1 — Proposal (no create_plan)
1. **Clarify** — Ask focused questions about scope, goals, constraints. Wait for answers.
2. **Propose tasks** — Write the task list in plain text (title + description using the template + required capability). Ask: "Does this look right? Anything to add or change?"
3. **Wait for confirmation** — Do NOT call `create_plan` yet. Stay in conversation until the user says "sounds good", "yes", or similar.

### Phase 2 — Creation (after user confirms)
4. **Create plan** — Call `create_plan(name, description)` once. Then call `create_plan_task(plan_id, title, description)` for each task. Use the task template structure.
5. **Assign agents** — Call `list_plan_assignees(plan_id)` to get valid agent IDs. Call `assign_plan_task(plan_id, task_id, agent_id)` for each. Show a summary.
6. **Activate** — Ask: "Should I start the plan?" Only call `activate_plan(plan_id)` when the user explicitly confirms.

### Key rules
- **Never call create_plan before user confirms** — proposal is text only; plan is created only after approval.
- **Never call create_plan twice** — if a draft plan exists, use that plan_id.
- **Never assign tasks to yourself** — you are the coordinator; all board tasks go to other agents. Synthesis, summaries, and wrap-up are done by you naturally after all tasks complete.
- **Never guess agent IDs** — always call `list_plan_assignees` first.

### Agent communication
- **Prefer task comments** (`add_task_comment`) — visible to all agents and the admin, creates a persistent record.
- Use `@agent_name` in comments to notify a specific agent.
- Before starting work, call `list_task_comments(plan_id, task_id)` to read prior context.
- Use `a2a_call` only for urgent real-time coordination (requires target agent to be running).

