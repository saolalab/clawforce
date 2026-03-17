"""Plan tools: full plan/task lifecycle via the admin API.

Agents can create plans, create tasks, assign tasks, update status, and add
artifacts. This moves all planning intelligence into the agent (LLM) layer —
the admin API is a pure CRUD backend.
"""

import asyncio
import io
from typing import Any

import httpx

from clawbot.agent.tools.base import Tool


def _extract_pdf_text(data: bytes) -> tuple[str | None, str | None]:
    """Extract text from PDF bytes.

    Returns:
        (text, error): text is the extracted content, error explains any failure.
        If text is not None, error is None. If text is None, error explains why.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return None, "pypdf library not installed"
    try:
        reader = PdfReader(io.BytesIO(data))
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(f"--- Page {i + 1} ---\n{text.strip()}")
        if pages_text:
            return "\n\n".join(pages_text), None
        return None, "PDF has no extractable text (may be image-based or scanned)"
    except Exception as e:
        return None, f"PDF parsing failed: {e}"


def _api_base(url: str) -> str:
    """Ensure admin URL has no trailing slash and includes /api if missing."""
    u = url.rstrip("/")
    if not u.endswith("/api"):
        u = f"{u}/api"
    return u


class _PlanToolBase(Tool):
    """Shared base for plan tools that call the admin API."""

    def __init__(self, admin_base_url: str, agent_token: str) -> None:
        self._base = _api_base(admin_base_url)
        self._token = agent_token

    async def _api_call(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        label: str,
        _retries: int = 2,
    ) -> dict | list | str:
        """Authenticated API call with retry on 5xx. Returns parsed JSON on success, error string on failure."""
        url = f"{self._base}{path}"
        headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        last_err = ""
        for attempt in range(_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    req_kwargs: dict[str, Any] = {}
                    if payload is not None:
                        req_kwargs["json"] = payload
                    r = await client.request(method, url, headers=headers, **req_kwargs)
                    r.raise_for_status()
                    return r.json()
            except httpx.HTTPStatusError as e:
                last_err = f"Error {label}: {e.response.status_code} {e.response.text}"
                if e.response.status_code < 500 or attempt == _retries:
                    return last_err
            except httpx.RequestError as e:
                last_err = f"Error calling admin API: {e!s}"
                if attempt == _retries:
                    return last_err
            await asyncio.sleep(0.3 * (attempt + 1))
        return last_err


# ── Read-only tools ──────────────────────────────────────────────────────


class ListPlansTool(_PlanToolBase):
    """List all plans visible to this agent."""

    @property
    def name(self) -> str:
        return "list_plans"

    @property
    def description(self) -> str:
        return "List all plans. Returns an array of plan summaries with id, name, status, and agent assignments."

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs: Any) -> str:
        result = await self._api_call("GET", "/plans", label="listing plans")
        if isinstance(result, str):
            return result
        if isinstance(result, list):
            if not result:
                return "No plans found."
            lines = []
            for p in result:
                status = p.get("status", "draft")
                agents = p.get("agentIds", [])
                tasks = p.get("tasks", [])
                line = (
                    f"- **{p.get('name', '?')}** (id={p['id']}, status={status}, "
                    f"{len(tasks)} tasks, {len(agents)} agents)"
                )
                if status == "paused":
                    line += " (PAUSED by admin — do not work on this plan)"
                elif status == "completed":
                    line += " (COMPLETED — all work is done, do not modify tasks)"
                lines.append(line)
            return "\n".join(lines)
        return str(result)


class PlanQueryTool(_PlanToolBase):
    """Query plans and tasks with filters — find tasks assigned to me, by status, etc."""

    def __init__(self, admin_base_url: str, agent_token: str, agent_id: str) -> None:
        super().__init__(admin_base_url, agent_token)
        self._agent_id = agent_id

    @property
    def name(self) -> str:
        return "plan_query"

    @property
    def description(self) -> str:
        return (
            "Query plans and tasks with filters. Use assigned_to_me=True to find tasks assigned to you — "
            "these are the tasks you should work on. You should only work on tasks assigned to you. "
            "Returns a focused view based on your query."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "Filter to a specific plan (optional — omit to query all plans)",
                },
                "assigned_to_me": {
                    "type": "boolean",
                    "description": "If true, only show tasks assigned to you (default: false)",
                },
                "status": {
                    "type": "string",
                    "enum": ["todo", "in-progress", "done", "all"],
                    "description": "Filter tasks by status/column (default: all)",
                },
                "unassigned_only": {
                    "type": "boolean",
                    "description": "If true, only show tasks with no agent assigned (default: false)",
                },
                "include_plan_status": {
                    "type": "boolean",
                    "description": "If true, include plan status summary (default: true)",
                },
            },
        }

    async def execute(
        self,
        plan_id: str = "",
        assigned_to_me: bool = False,
        status: str = "all",
        unassigned_only: bool = False,
        include_plan_status: bool = True,
        **kwargs: Any,
    ) -> str:
        result = await self._api_call("GET", "/plans", label="querying plans")
        if isinstance(result, str):
            return result
        if not isinstance(result, list):
            return str(result)

        plans = result
        if plan_id:
            plans = [p for p in plans if p.get("id") == plan_id]
            if not plans:
                return f"Plan not found: {plan_id}"

        status_to_suffix = {
            "todo": "col-todo",
            "in-progress": "col-in-progress",
            "done": "col-done",
        }
        column_suffix = status_to_suffix.get(status)

        lines: list[str] = []

        for plan in plans:
            plan_name = plan.get("name", "?")
            plan_status = plan.get("status", "draft")
            agent_ids = plan.get("agentIds", [])
            tasks = plan.get("tasks", [])

            if self._agent_id not in agent_ids and not plan_id:
                continue

            filtered_tasks = tasks
            if assigned_to_me:
                filtered_tasks = [t for t in filtered_tasks if t.get("agent_id") == self._agent_id]
            if unassigned_only:
                filtered_tasks = [t for t in filtered_tasks if not t.get("agent_id")]
            if column_suffix:
                filtered_tasks = [
                    t for t in filtered_tasks if t.get("column_id", "").endswith(column_suffix)
                ]

            if include_plan_status:
                todo_count = len([t for t in tasks if t.get("column_id", "").endswith("col-todo")])
                in_progress_count = len(
                    [t for t in tasks if t.get("column_id", "").endswith("col-in-progress")]
                )
                done_count = len([t for t in tasks if t.get("column_id", "").endswith("col-done")])
                my_tasks_count = len([t for t in tasks if t.get("agent_id") == self._agent_id])

                lines.append(f"## Plan: {plan_name}")
                lines.append(f"- **ID:** {plan['id']}")
                lines.append(f"- **Status:** {plan_status}")
                if plan_status == "paused":
                    lines.append(
                        "- **WARNING:** This plan is paused by admin. Do not work on it until re-activated."
                    )
                elif plan_status == "completed":
                    lines.append(
                        "- **INFO:** This plan is completed. All work is done — do not create or modify tasks."
                    )
                lines.append(
                    f"- **Progress:** {done_count}/{len(tasks)} done "
                    f"({todo_count} todo, {in_progress_count} in progress)"
                )
                lines.append(f"- **Your tasks:** {my_tasks_count}")
                lines.append("")

            if filtered_tasks:
                filter_desc = []
                if assigned_to_me:
                    filter_desc.append("assigned to you")
                if unassigned_only:
                    filter_desc.append("unassigned")
                if column_suffix:
                    filter_desc.append(f"status={status}")
                filter_label = f" ({', '.join(filter_desc)})" if filter_desc else ""

                lines.append(f"### Tasks{filter_label}")
                for t in sorted(filtered_tasks, key=lambda x: x.get("position", 0)):
                    col_id = t.get("column_id", "")
                    col_label = (
                        "Todo"
                        if col_id.endswith("col-todo")
                        else "In Progress"
                        if col_id.endswith("col-in-progress")
                        else "Blocked"
                        if col_id.endswith("col-blocked")
                        else "Done"
                        if col_id.endswith("col-done")
                        else col_id
                    )
                    agent = t.get("agent_id") or "unassigned"
                    lines.append(f"- **[{t['id']}]** {t.get('title', '?')}")
                    lines.append(f"  Status: {col_label} | Assigned: {agent}")
                    if t.get("description"):
                        lines.append(f"  {t['description'][:100]}...")
                lines.append("")
            elif assigned_to_me or unassigned_only or column_suffix:
                lines.append("### Tasks")
                lines.append("  (no tasks match your query)")
                lines.append("")

        if not lines:
            if plan_id:
                return f"You are not assigned to plan {plan_id}."
            return "No plans found where you are assigned."

        return "\n".join(lines)


class GetPlanTool(_PlanToolBase):
    """Get full details of a plan including all columns, tasks, and agent assignments."""

    @property
    def name(self) -> str:
        return "get_plan"

    @property
    def description(self) -> str:
        return (
            "Get full plan details: columns, tasks (with assignment and status), and assigned agents. "
            "Use this to understand what work exists and what needs to be done."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID to retrieve"},
            },
            "required": ["plan_id"],
        }

    async def execute(self, plan_id: str, **kwargs: Any) -> str:
        result = await self._api_call("GET", f"/plans/{plan_id}", label="getting plan")
        if isinstance(result, str):
            return result
        if not isinstance(result, dict):
            return str(result)

        plan_status = result.get("status", "draft")
        lines = [
            f"# Plan: {result.get('name', '?')}",
            f"ID: {result['id']}",
            f"Status: {plan_status}",
            f"Description: {result.get('description') or '(none)'}",
            f"Assigned agents: {', '.join(result.get('agentIds', [])) or '(none)'}",
            "",
        ]
        if plan_status == "paused":
            lines.append(
                "WARNING: This plan is paused by admin. Do not create or update tasks until re-activated."
            )
            lines.append("")
        elif plan_status == "completed":
            lines.append(
                "INFO: This plan is completed. All work is done — do not create or modify any tasks."
            )
            lines.append("")
        columns = sorted(result.get("columns", []), key=lambda c: c.get("position", 0))
        tasks = result.get("tasks", [])
        for col in columns:
            lines.append(f"## {col.get('title', '?')} ({col['id']})")
            col_tasks = sorted(
                [t for t in tasks if t.get("column_id") == col["id"]],
                key=lambda t: t.get("position", 0),
            )
            if not col_tasks:
                lines.append("  (no tasks)")
            for t in col_tasks:
                agent = t.get("agent_id") or "unassigned"
                lines.append(f"  - [{t['id']}] {t.get('title', '?')} (agent: {agent})")
                if t.get("description"):
                    lines.append(f"    {t['description']}")
            lines.append("")
        return "\n".join(lines)


# ── Write tools ──────────────────────────────────────────────────────────


class CreatePlanTool(_PlanToolBase):
    """Create a new plan. Returns the plan ID for subsequent task creation."""

    @property
    def name(self) -> str:
        return "create_plan"

    @property
    def description(self) -> str:
        return (
            "Create a new plan (project board). Use this to organize work into a Kanban board "
            "with Todo / In Progress / Done columns. Returns the new plan's ID.\n\n"
            "PLAN LIFECYCLE — call create_plan ONLY after user confirms:\n"
            "1. BEFORE create_plan (proposal phase): Clarify scope, propose task breakdown in plain text, "
            "ask 'Does this look right?' — do NOT call create_plan yet.\n"
            "2. AFTER user confirms (e.g. 'sounds good', 'yes'): Call create_plan ONCE, then "
            "create_plan_task for each task, then assign_plan_task, then activate_plan.\n\n"
            "If a draft or active plan already exists (same name), use that plan_id — "
            "do NOT call create_plan again. Check list_plans() first if unsure."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Plan name (short, descriptive)"},
                "description": {"type": "string", "description": "Plan description and goals"},
            },
            "required": ["name"],
        }

    async def execute(self, name: str, description: str = "", **kwargs: Any) -> str:
        # Guard: check for existing plans to avoid duplicates
        existing = await self._api_call("GET", "/plans", label="checking existing plans")
        if isinstance(existing, list):
            name_lower = name.strip().lower()
            for p in existing:
                existing_id = p.get("id", "")
                existing_name = p.get("name", "")
                status = p.get("status", "draft")
                existing_name_lower = (existing_name or "").strip().lower()

                if status == "draft" and existing_name_lower == name_lower:
                    return (
                        f"A draft plan with this name already exists: **{existing_name}** (id={existing_id}).\n\n"
                        f"Do NOT call create_plan again — use plan_id='{existing_id}' for all subsequent calls.\n"
                        f"If the user has confirmed the proposal: create tasks with create_plan_task, then assign, then activate.\n"
                        f"If still in proposal phase: continue the conversation in text; do not create a plan yet."
                    )
                if status == "active" and existing_name_lower == name_lower:
                    return (
                        f"A plan with the same name is already **active**: **{existing_name}** (id={existing_id}).\n\n"
                        f"Do NOT create a duplicate plan. Use plan_id='{existing_id}' — the plan and tasks already exist.\n"
                        f"If the user asked 'why' or similar: explain what happened, reference the existing plan, "
                        f"or use get_plan(plan_id='{existing_id}') to show current status. Never create the same plan twice."
                    )

        result = await self._api_call(
            "POST",
            "/plans",
            {"name": name, "description": description},
            label="creating plan",
        )
        if isinstance(result, str):
            return result
        plan_id = result.get("id", "")
        return (
            f"Plan created: {name} (id={plan_id}). User has confirmed — proceed with task creation.\n\n"
            f"**Your role: coordinator.** You plan, delegate, and review. "
            f"Do NOT assign tasks to yourself — all board tasks go to other agents. "
            f"Synthesis, summaries, and wrap-up are done by you naturally after all tasks complete.\n\n"
            f"**Next steps (in order):**\n\n"
            f"**Step 1 — Create tasks (unassigned)**\n"
            f"Call `create_plan_task(plan_id='{plan_id}', title=..., description=...)` for each task. "
            f"Do NOT set agent_id — tasks are created unassigned.\n\n"
            f"**Step 2 — Assign agents**\n"
            f"Call `list_plan_assignees(plan_id='{plan_id}')` to get valid agent IDs and their capabilities. "
            f"Match each task to the best-suited agent, then call `assign_plan_task(plan_id, task_id, agent_id)` for each. "
            f"Only use IDs from list_plan_assignees — never guess.\n\n"
            f"**Step 3 — Activate (only after user confirms 'start')**\n"
            f'Show the user a summary of assignments, then ask: "Should I start the plan?" '
            f"Only call `activate_plan(plan_id='{plan_id}')` when the user explicitly says yes/start/go.\n\n"
            f"Do NOT call create_plan again — you already have plan_id={plan_id}."
        )


class DeletePlanTool(_PlanToolBase):
    """Delete a plan and all its tasks, artifacts, and comments."""

    @property
    def name(self) -> str:
        return "delete_plan"

    @property
    def description(self) -> str:
        return (
            "Delete a plan permanently. This removes the plan and ALL its tasks, artifacts, "
            "and comments. This action cannot be undone. Use with caution."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID to delete"},
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to confirm deletion. Safety check to prevent accidental deletion.",
                },
            },
            "required": ["plan_id", "confirm"],
        }

    async def execute(self, plan_id: str, confirm: bool = False, **kwargs: Any) -> str:
        if not confirm:
            return (
                "Deletion not confirmed. Set confirm=true to delete the plan. "
                "WARNING: This will permanently delete the plan and all its tasks, artifacts, and comments."
            )
        result = await self._api_call(
            "DELETE",
            f"/plans/{plan_id}",
            None,
            label="deleting plan",
        )
        if isinstance(result, str):
            return result
        return f"Plan {plan_id} has been permanently deleted along with all its tasks, artifacts, and comments."


class ActivatePlanTool(_PlanToolBase):
    """Activate a plan — marks it ready. Running agents receive context; coordinator engages others via plan assistant when needed."""

    @property
    def name(self) -> str:
        return "activate_plan"

    @property
    def description(self) -> str:
        return (
            "Activate a plan after all tasks have been created and assigned. "
            "Plan status becomes 'active'. Running agents receive their task context; "
            "you decide when to engage others via the plan assistant (not all agents need to work at once). "
            "Only call this once all tasks are created and assigned to specific agents."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID to activate"},
            },
            "required": ["plan_id"],
        }

    async def execute(self, plan_id: str, **kwargs: Any) -> str:
        result = await self._api_call(
            "POST",
            f"/plans/{plan_id}/activate",
            None,
            label="activating plan",
        )
        if isinstance(result, str):
            return result
        status = result.get("status", "active")
        return (
            f"Plan {plan_id} is now active. Status: {status}. "
            f"Running agents received context; use the plan assistant to engage others when ready."
        )


class CreatePlanTaskTool(_PlanToolBase):
    """Create a task within a plan (without assignment — use assign_plan_task after)."""

    @property
    def name(self) -> str:
        return "create_plan_task"

    @property
    def description(self) -> str:
        return (
            "Create a new task in a plan. Tasks are created UNASSIGNED by default. "
            "After creating all tasks, call list_plan_assignees(plan_id) to see available agents, "
            "then use assign_plan_task(plan_id, task_id, agent_id) to assign each task to an agent. "
            "CRITICAL: Use the task template structure for description — include Context, Requirements, "
            "Definition of Done, and Output sections. For code tasks (pull, implement, PR, report), "
            "explicitly state that workflow and where to report (task comment or artifact)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan to add the task to"},
                "title": {
                    "type": "string",
                    "description": "Clear, imperative task title (e.g., 'Implement user authentication API')",
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Task description MUST follow this template structure (markdown):\n"
                        "## Context — why this task exists, background\n"
                        "## Requirements — specific deliverables, what to build/change\n"
                        "## Definition of Done — checklist of verifiable criteria (- [ ] item)\n"
                        "## Output — where to report: add_task_comment, add_plan_artifact, PR comment, etc.\n\n"
                        "For code tasks (pull from repo, implement, commit, PR, report): "
                        "include the workflow in Requirements and specify Output (e.g. 'add_task_comment with summary + add_plan_artifact(report.md)'). "
                        "Write as if the assigned agent has no prior context."
                    ),
                },
                "column_id": {
                    "type": "string",
                    "enum": ["col-todo", "col-in-progress", "col-done"],
                    "description": "Column to place the task in (default: col-todo)",
                },
            },
            "required": ["plan_id", "title", "description"],
        }

    async def execute(
        self,
        plan_id: str,
        title: str,
        description: str = "",
        column_id: str = "col-todo",
        **kwargs: Any,
    ) -> str:
        desc_words = len(description.split()) if description else 0
        if desc_words < 30:
            return (
                f"Error: Task description is too brief ({desc_words} words). "
                "Use the task template: ## Context, ## Requirements, ## Definition of Done, ## Output. "
                "Include at least 30 words so the assigned agent can execute without clarification."
            )

        payload = {
            "column_id": column_id,
            "title": title,
            "description": description,
            "agent_id": "",
        }
        result = await self._api_call(
            "POST",
            f"/plans/{plan_id}/tasks",
            payload,
            label="creating task",
        )
        if isinstance(result, str):
            return result
        task_id = result.get("id", "")
        return (
            f"Task created: {title} (id={task_id}, column={column_id}, unassigned). "
            f"Use assign_plan_task(plan_id='{plan_id}', task_id='{task_id}', agent_id=...) to assign it."
        )


class AssignPlanTaskTool(_PlanToolBase):
    """Assign a plan task to a specific agent (separate from task creation)."""

    def __init__(self, admin_base_url: str, agent_token: str, coordinator_id: str = "") -> None:
        super().__init__(admin_base_url, agent_token)
        self._coordinator_id = coordinator_id

    @property
    def name(self) -> str:
        return "assign_plan_task"

    @property
    def description(self) -> str:
        return (
            "Assign a plan task to a specific agent. "
            "ALWAYS call list_plan_assignees(plan_id) first to get valid agent IDs and their descriptions. "
            "Only assign to agents returned by list_plan_assignees — never guess or invent agent IDs. "
            "Agents can be assigned multiple tasks; consider workload when assigning. "
            "Do NOT assign tasks to yourself — you are the coordinator. Your role is to plan, delegate, "
            "and review. Synthesis, summaries, and wrap-up happen naturally after all tasks complete, "
            "without needing a formal task assignment."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID"},
                "task_id": {"type": "string", "description": "The task ID to assign"},
                "agent_id": {
                    "type": "string",
                    "description": (
                        "Agent ID to assign the task to. "
                        "Must be an ID returned by list_plan_assignees(plan_id). "
                        "Do NOT guess or use agent names — use the exact id field."
                    ),
                },
            },
            "required": ["plan_id", "task_id", "agent_id"],
        }

    async def execute(
        self,
        plan_id: str,
        task_id: str,
        agent_id: str,
        **kwargs: Any,
    ) -> str:
        if not agent_id:
            return "Error: agent_id is required. Call list_plan_assignees(plan_id) to see valid agent IDs."

        # Block coordinator from assigning tasks to themselves
        if self._coordinator_id and agent_id == self._coordinator_id:
            return (
                "Error: You cannot assign a task to yourself. "
                "You are the coordinator — your role is to plan, delegate, and review. "
                "Synthesis, summaries, and wrap-up work happens naturally after all agent tasks "
                "complete; it does not need a formal task on the board. "
                "Call list_plan_assignees(plan_id) to find the right agent for this task."
            )

        # Validate agent_id exists in the plan assignees list
        assignees_result = await self._api_call(
            "GET", f"/plans/{plan_id}/assignees", label="validating assignee"
        )
        if isinstance(assignees_result, list):
            valid_ids = {a.get("id") for a in assignees_result}
            if agent_id not in valid_ids:
                available = ", ".join(
                    f"{a.get('name', a.get('id'))} (id={a.get('id')})"
                    for a in assignees_result
                    if a.get("id") != self._coordinator_id
                )
                return (
                    f"Error: Agent '{agent_id}' is not a valid assignee for this plan. "
                    f"Call list_plan_assignees(plan_id='{plan_id}') to see valid agents. "
                    f"Available: {available or '(none)'}"
                )

        result = await self._api_call(
            "PUT",
            f"/plans/{plan_id}/tasks/{task_id}",
            {"agent_id": agent_id},
            label="assigning task",
        )
        if isinstance(result, str):
            return result
        task_title = result.get("title", task_id)
        return f"Task '{task_title}' (id={task_id}) assigned to agent {agent_id}."


class UpdatePlanTaskTool(_PlanToolBase):
    """Update a plan task's status, title, or description (not for initial assignment)."""

    @property
    def name(self) -> str:
        return "update_plan_task"

    @property
    def description(self) -> str:
        return (
            "Update a plan task's status (column), title, or description. "
            "Use to move tasks between columns (col-todo, col-in-progress, col-done). "
            "For initial task assignment use assign_plan_task instead. "
            "When updating description, ensure it remains detailed and actionable."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID"},
                "task_id": {"type": "string", "description": "The task ID to update"},
                "column_id": {
                    "type": "string",
                    "enum": ["col-todo", "col-in-progress", "col-done"],
                    "description": "New column (status)",
                },
                "agent_id": {"type": "string", "description": "New agent assignment"},
                "title": {"type": "string", "description": "New title (clear, imperative)"},
                "description": {
                    "type": "string",
                    "description": (
                        "New description. If updating, include: context, requirements, "
                        "acceptance criteria, and technical notes. Keep it detailed (4-10 sentences)."
                    ),
                },
            },
            "required": ["plan_id", "task_id"],
        }

    async def execute(
        self,
        plan_id: str,
        task_id: str,
        column_id: str | None = None,
        agent_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> str:
        payload: dict[str, Any] = {}
        if column_id is not None:
            payload["column_id"] = column_id
        if agent_id is not None:
            payload["agent_id"] = agent_id
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if not payload:
            return "Nothing to update — provide at least one field."
        result = await self._api_call(
            "PUT",
            f"/plans/{plan_id}/tasks/{task_id}",
            payload,
            label="updating task",
        )
        if isinstance(result, str):
            return result
        changes = ", ".join(f"{k}={v}" for k, v in payload.items())
        return f"Task {task_id} updated: {changes}."


class AddPlanArtifactTool(_PlanToolBase):
    """Add an artifact (output, summary, file content) to a plan."""

    @property
    def name(self) -> str:
        return "add_plan_artifact"

    @property
    def description(self) -> str:
        return (
            "Add an artifact to the plan (stored on admin). Use for summaries, outputs, or deliverables. "
            "plan_id from plan context; task_id optional (link to a specific task). "
            "Prefer .md extension for text artifacts so they render as Markdown in the browser."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID"},
                "task_id": {
                    "type": "string",
                    "description": "Optional task ID this artifact relates to",
                },
                "name": {
                    "type": "string",
                    "description": (
                        "Filename for the artifact. Use .md extension for text/report artifacts "
                        "(e.g. 'summary.md', 'report.md') so they open as Markdown in the browser. "
                        "Only use other extensions (e.g. .json, .csv) when the content is a specific format."
                    ),
                },
                "content": {"type": "string", "description": "The artifact content (text)"},
            },
            "required": ["plan_id", "name", "content"],
        }

    @staticmethod
    def _infer_content_type(name: str) -> str:
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        return {
            "md": "text/markdown",
            "json": "application/json",
            "yaml": "application/yaml",
            "yml": "application/yaml",
            "csv": "text/csv",
            "html": "text/html",
            "xml": "application/xml",
            "js": "application/javascript",
            "py": "text/x-python",
            "sh": "text/x-sh",
        }.get(ext, "text/plain")

    async def execute(
        self,
        plan_id: str,
        name: str,
        content: str,
        task_id: str = "",
        **kwargs: Any,
    ) -> str:
        content_type = self._infer_content_type(name)
        payload = {
            "name": name,
            "content": content,
            "task_id": task_id,
            "content_type": content_type,
        }
        result = await self._api_call(
            "POST", f"/plans/{plan_id}/artifacts", payload, label="adding artifact"
        )
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return f"Artifact added: {name} (id={result.get('id', '')})."
        return str(result)


class ListPlanArtifactsTool(_PlanToolBase):
    """List all artifacts in a plan, optionally filtered by task."""

    @property
    def name(self) -> str:
        return "list_plan_artifacts"

    @property
    def description(self) -> str:
        return (
            "List all artifacts in a plan. Returns artifact metadata including id, name, type, and size. "
            "Use task_id to filter artifacts for a specific task. Use get_plan_artifact to read content."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID"},
                "task_id": {
                    "type": "string",
                    "description": "Optional task ID to filter artifacts for a specific task",
                },
            },
            "required": ["plan_id"],
        }

    async def execute(
        self,
        plan_id: str,
        task_id: str = "",
        **kwargs: Any,
    ) -> str:
        path = f"/plans/{plan_id}/artifacts"
        if task_id:
            path = f"{path}?task_id={task_id}"
        result = await self._api_call("GET", path, label="listing artifacts")
        if isinstance(result, str):
            return result
        if isinstance(result, list):
            if not result:
                filter_msg = f" for task {task_id}" if task_id else ""
                return f"No artifacts found in plan {plan_id}{filter_msg}."
            lines = [f"## Artifacts in plan {plan_id}"]
            if task_id:
                lines[0] += f" (task: {task_id})"
            lines.append("")
            for a in result:
                name = a.get("name", "unnamed")
                artifact_id = a.get("id", "?")
                content_type = a.get("content_type", "text/plain")
                size = a.get("size", 0)
                task = a.get("task_id", "")
                is_file = bool(a.get("file_path"))
                type_label = "file" if is_file else "text"
                size_str = f"{size} bytes" if size < 1024 else f"{size // 1024} KB"
                task_str = f", task={task}" if task else ""
                lines.append(
                    f"- **{name}** (id=`{artifact_id}`, {type_label}, {content_type}, {size_str}{task_str})"
                )
            lines.append("")
            lines.append("Use `get_plan_artifact(plan_id, artifact_id)` to read artifact content.")
            return "\n".join(lines)
        return str(result)


class GetPlanArtifactTool(_PlanToolBase):
    """Get/download a plan artifact's content."""

    @property
    def name(self) -> str:
        return "get_plan_artifact"

    @property
    def description(self) -> str:
        return (
            "Get the content of a plan artifact. For text artifacts, returns the content directly. "
            "For file artifacts (binary), downloads and returns the content. "
            "Use list_plan_artifacts first to find artifact IDs."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID"},
                "artifact_id": {"type": "string", "description": "The artifact ID to retrieve"},
            },
            "required": ["plan_id", "artifact_id"],
        }

    async def _download_file(self, plan_id: str, artifact_id: str) -> str | bytes:
        """Download binary artifact content."""
        url = f"{self._base}/plans/{plan_id}/artifacts/{artifact_id}/download"
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(url, headers=headers)
                r.raise_for_status()
                return r.content
        except httpx.HTTPStatusError as e:
            return f"Error downloading artifact: {e.response.status_code} {e.response.text}"
        except httpx.RequestError as e:
            return f"Error downloading artifact: {e!s}"

    async def execute(
        self,
        plan_id: str,
        artifact_id: str,
        **kwargs: Any,
    ) -> str:
        result = await self._api_call(
            "GET", f"/plans/{plan_id}/artifacts/{artifact_id}", label="getting artifact"
        )
        if isinstance(result, str):
            return result
        if not isinstance(result, dict):
            return str(result)

        name = result.get("name", "unnamed")
        content_type = result.get("content_type", "text/plain")
        file_path = result.get("file_path", "")
        content = result.get("content", "")
        size = result.get("size", 0)

        if not file_path and content:
            return (
                f"## Artifact: {name}\n"
                f"**Type:** {content_type} | **Size:** {size} bytes\n\n"
                f"### Content\n```\n{content}\n```"
            )

        if file_path:
            data = await self._download_file(plan_id, artifact_id)
            if isinstance(data, str):
                return data

            is_text = content_type.startswith("text/") or content_type in (
                "application/json",
                "application/xml",
                "application/javascript",
                "application/x-yaml",
                "application/yaml",
            )
            if is_text:
                try:
                    text_content = data.decode("utf-8")
                    return (
                        f"## Artifact: {name}\n"
                        f"**Type:** {content_type} | **Size:** {len(data)} bytes\n\n"
                        f"### Content\n```\n{text_content}\n```"
                    )
                except UnicodeDecodeError:
                    pass

            if content_type == "application/pdf":
                pdf_text, pdf_error = _extract_pdf_text(data)
                if pdf_text:
                    return (
                        f"## Artifact: {name}\n"
                        f"**Type:** PDF | **Size:** {len(data)} bytes\n\n"
                        f"### Extracted Text\n{pdf_text}"
                    )
                return (
                    f"## Artifact: {name}\n"
                    f"**Type:** PDF | **Size:** {len(data)} bytes\n\n"
                    f"Could not extract text: {pdf_error}\n"
                    f"To work with this file, save it to your workspace using write_file."
                )

            return (
                f"## Artifact: {name}\n"
                f"**Type:** {content_type} | **Size:** {len(data)} bytes\n\n"
                f"This is a binary file. First {min(200, len(data))} bytes (hex):\n"
                f"```\n{data[:200].hex()}\n```\n\n"
                f"To work with this file, save it to your workspace using write_file."
            )

        return f"Artifact {artifact_id} exists but has no content."


# ── Comment tools ─────────────────────────────────────────────────────────


class AddTaskCommentTool(_PlanToolBase):
    """Add a comment to a plan task. Supports @mentions to notify other agents."""

    @property
    def name(self) -> str:
        return "add_task_comment"

    @property
    def description(self) -> str:
        return (
            "Add a comment to a plan task. Use @agent_name or @agent_id to mention "
            "and notify other agents. Comments are visible to all agents on the plan."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID"},
                "task_id": {"type": "string", "description": "The task ID to comment on"},
                "content": {
                    "type": "string",
                    "description": "Comment text. Use @agent_name to mention agents.",
                },
            },
            "required": ["plan_id", "task_id", "content"],
        }

    async def execute(
        self,
        plan_id: str,
        task_id: str,
        content: str,
        **kwargs: Any,
    ) -> str:
        if not content.strip():
            return "Error: comment content cannot be empty"

        result = await self._api_call(
            "POST",
            f"/plans/{plan_id}/tasks/{task_id}/comments",
            {"content": content},
            label="adding comment",
        )
        if isinstance(result, str):
            return result
        comment_id = result.get("id", "")
        return f"Comment added to task {task_id} (id={comment_id})."


class ListTaskCommentsTool(_PlanToolBase):
    """List comments on a plan task."""

    @property
    def name(self) -> str:
        return "list_task_comments"

    @property
    def description(self) -> str:
        return "List all comments on a plan task. Shows author, timestamp, and content."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan ID"},
                "task_id": {"type": "string", "description": "The task ID"},
            },
            "required": ["plan_id", "task_id"],
        }

    async def execute(
        self,
        plan_id: str,
        task_id: str,
        **kwargs: Any,
    ) -> str:
        result = await self._api_call(
            "GET",
            f"/plans/{plan_id}/tasks/{task_id}/comments",
            label="listing comments",
        )
        if isinstance(result, str):
            return result
        if not isinstance(result, list):
            return str(result)
        if not result:
            return f"No comments on task {task_id}."

        lines = [f"## Comments on task {task_id}\n"]
        for c in result:
            author = c.get("author_name", c.get("author_id", "?"))
            author_type = c.get("author_type", "")
            created = c.get("created_at", "")[:16].replace("T", " ")
            content = c.get("content", "")
            type_label = f" ({author_type})" if author_type else ""
            lines.append(f"**{author}**{type_label} — {created}")
            lines.append(f"> {content}")
            lines.append("")
        return "\n".join(lines)


class ListPlanAssigneesTool(_PlanToolBase):
    """List all agents available to work on a plan (for task assignment)."""

    @property
    def name(self) -> str:
        return "list_plan_assignees"

    @property
    def description(self) -> str:
        return (
            "List all agents available to be assigned tasks on a plan. "
            "Use ONLY when assigning tasks to a plan — NOT for general questions about peers or teammates. "
            "For 'who are your peers?' use a2a_discover instead. "
            "Returns each agent's id, name, description, running status, and whether they are "
            "already assigned to the plan. Use this before creating tasks so you know which "
            "agent IDs to use in the agent_id field of create_plan_task."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "The plan ID to list assignees for",
                },
            },
            "required": ["plan_id"],
        }

    async def execute(self, plan_id: str, **kwargs: Any) -> str:
        result = await self._api_call(
            "GET", f"/plans/{plan_id}/assignees", label="listing plan assignees"
        )
        if isinstance(result, str):
            return result
        if not isinstance(result, list):
            return str(result)

        if not result:
            return "No agents are available for task assignment. Ask the user to add agents to the system first."

        lines = ["## Available agents for task assignment", ""]
        for a in result:
            status = a.get("status", "unknown")
            assigned = " [already assigned to plan]" if a.get("assigned") else ""
            desc = a.get("description", "")
            desc_str = f" — {desc}" if desc else ""
            lines.append(f"- **{a.get('name', a['id'])}** (id=`{a['id']}`){assigned}")
            lines.append(f"  Status: {status}{desc_str}")
        lines.append("")
        lines.append(
            "Use the agent `id` in `assign_plan_task(plan_id, task_id, agent_id)` to assign tasks. "
            "Assign each task to the agent whose description best matches the work."
        )
        return "\n".join(lines)


# ── Registration helper ──────────────────────────────────────────────────


def get_plan_tools(admin_base_url: str, agent_token: str, agent_id: str = "") -> list[Tool]:
    """Return all plan tools configured for the given admin API."""
    tools: list[Tool] = [
        ListPlansTool(admin_base_url, agent_token),
        GetPlanTool(admin_base_url, agent_token),
        ListPlanAssigneesTool(admin_base_url, agent_token),
        CreatePlanTool(admin_base_url, agent_token),
        DeletePlanTool(admin_base_url, agent_token),
        ActivatePlanTool(admin_base_url, agent_token),
        CreatePlanTaskTool(admin_base_url, agent_token),
        AssignPlanTaskTool(admin_base_url, agent_token, coordinator_id=agent_id),
        UpdatePlanTaskTool(admin_base_url, agent_token),
        AddPlanArtifactTool(admin_base_url, agent_token),
        ListPlanArtifactsTool(admin_base_url, agent_token),
        GetPlanArtifactTool(admin_base_url, agent_token),
        AddTaskCommentTool(admin_base_url, agent_token),
        ListTaskCommentsTool(admin_base_url, agent_token),
    ]
    if agent_id:
        tools.append(PlanQueryTool(admin_base_url, agent_token, agent_id))
    return tools
