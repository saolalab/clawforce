"""Plan CRUD, tasks, agent assignment, and start/stop.

Planning intelligence lives in the agent layer — agents use plan tools
(create_plan, create_plan_task, update_plan_task, etc.) to manage work.
The admin API is a pure CRUD backend.
"""

import asyncio
import json
import logging
import re as _re

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sse_starlette.sse import EventSourceResponse

from clawforce.auth import decode_token, get_current_user, get_user_or_agent
from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.plan_access import require_plan_access
from clawforce.core.store.agents import AgentStore
from clawforce.core.store.plan_artifacts import PlanArtifactStore
from clawforce.core.store.plans import PlanStore
from clawforce.core.stream_token import verify_stream_token
from clawforce.deps import (
    get_activity_events_store,
    get_agent_store,
    get_plan_artifact_store,
    get_plan_store,
    get_runtime,
)
from clawlib.activity import ActivityEvent

_PLAN_LOG_POLL_INTERVAL = 0.3  # seconds between DB polls for new plan activity events


class PlanCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str = ""


class PlanUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    description: str | None = None
    status: str | None = None


class TaskCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    column_id: str
    title: str = ""
    description: str = ""
    agent_id: str = ""


class TaskUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    description: str | None = None
    column_id: str | None = None
    agent_id: str | None = None
    position: int | None = None


class CommentCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str


class ArtifactCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = ""
    name: str = ""
    content_type: str = "text/plain"
    content: str = ""


class ArtifactRename(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    new_name: str


class ArtifactMove(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = ""


logger = logging.getLogger(__name__)

router = APIRouter(tags=["plans"])


def _plan_response(plan) -> dict:
    return plan.model_dump()


def _build_plan_context_message(plan, agent_id: str = "") -> str:
    """Build a per-agent text message describing the plan and the agent's specific tasks."""
    my_tasks = [t for t in plan.tasks if t.agent_id == agent_id] if agent_id else []

    lines = [
        f"# Plan: {plan.name}",
        f"Plan ID: `{plan.id}`",
        f"Status: {plan.status}",
        "",
        plan.description or "(No description)",
        "",
        "## Plan-scoped conversation",
        "This thread is for this plan. Full history is here. Use get_plan(plan_id) for full board if needed.",
        "",
    ]

    if agent_id:
        lines.extend(
            [
                "## Your assigned tasks",
                f"You have **{len(my_tasks)}** task(s) assigned to you on this plan.",
                "**Work ONLY on tasks assigned to you.** Do not pick up or execute tasks assigned to other agents.",
                "",
            ]
        )
        if my_tasks:
            for t in sorted(my_tasks, key=lambda t: t.position):
                col_label = (
                    "Todo"
                    if t.column_id.endswith("col-todo")
                    else "In Progress"
                    if t.column_id.endswith("col-in-progress")
                    else "Done"
                    if t.column_id.endswith("col-done")
                    else "Blocked"
                    if t.column_id.endswith("col-blocked")
                    else t.column_id
                )
                lines.append(f"- **[{t.id}]** {t.title} (status: {col_label})")
                if t.description:
                    lines.append(f"  {t.description}")
            lines.append("")
        else:
            lines.append(
                "No tasks are currently assigned to you. Check back after the plan creator assigns work."
            )
            lines.append("")

    lines.append("## Full plan board")
    for col in sorted(plan.columns, key=lambda c: c.position):
        lines.append(f"\n### {col.title}")
        tasks_in_col = [t for t in plan.tasks if t.column_id == col.id]
        for t in sorted(tasks_in_col, key=lambda t: t.position):
            assigned_marker = " ← **YOUR TASK**" if t.agent_id == agent_id and agent_id else ""
            agent_label = f" (agent: {t.agent_id})" if t.agent_id else " (unassigned)"
            desc = (
                f": {t.description[:80]}..."
                if t.description and len(t.description) > 80
                else (f": {t.description}" if t.description else "")
            )
            lines.append(f"- Task ID `{t.id}`: {t.title}{agent_label}{assigned_marker}{desc}")

    lines.extend(
        [
            "",
            "## Your role",
            "You are one of the agents assigned to this plan.",
            "",
            "**You CAN:** update your own tasks (move between columns, edit title/description), assign tasks to yourself, add and read artifacts, add comments, activate plans you are assigned to.",
            "",
            "**You CANNOT:** move tasks that are assigned to other agents, pause or deactivate plans (admin only), add or remove agents from the plan (admin only), delete plans or tasks or artifacts.",
            "",
            "## Communication",
            "Use `add_task_comment` for all updates — status, blockers, handoffs. Use @agent_name to notify. Call `list_task_comments` before starting. Use `a2a_call` only for urgent real-time coordination.",
            "",
            "## Artifacts",
            "Task deliverable: `add_plan_artifact(plan_id, name, content, task_id=task_id)`. Shared report: omit task_id. Use clear filenames (e.g. report.md).",
            "",
        ]
    )
    if plan.status == "paused":
        lines.extend(
            [
                "**This plan is currently PAUSED by admin.** Do not create or update tasks on it. Wait for admin to re-activate the plan.",
                "",
            ]
        )
    elif plan.status == "active" and my_tasks:
        lines.extend(
            [
                "## 🚀 Action required",
                "The plan is **active**. You have tasks assigned to you — **start working on them now.**",
                "Tasks follow: Context, Requirements, Definition of Done, Output. Report per the Output section (add_task_comment, add_plan_artifact).",
                "1. Move your task(s) to **In Progress** using `update_plan_task(plan_id, task_id, column_id='col-in-progress')`.",
                "2. Do the actual work described in each task.",
                "3. Save any output using `add_plan_artifact(plan_id, name, content, task_id=task_id)`. Use a `.md` filename (e.g. `report.md`) for text outputs so they render as Markdown in the browser.",
                "4. When done, move the task to **Done** using `update_plan_task(plan_id, task_id, column_id='col-done')`.",
                "5. Add a completion comment with `add_task_comment(plan_id, task_id, content)` summarising what you produced.",
                "",
                "Do NOT wait for further instructions. Start immediately.",
                "",
            ]
        )
    lines.extend(
        [
            "## Plan tools",
            "- list_plan_assignees(plan_id) — list ALL available agents for task assignment (always call this before assigning)",
            "- list_plans() — list all plans (shows status; respect paused plans)",
            "- get_plan(plan_id) — get full plan details with tasks and assignments",
            "- plan_query(plan_id?, assigned_to_me=True) — see only your assigned tasks",
            "- create_plan(name, description?) — create a new plan (you are auto-assigned as coordinator)",
            "- activate_plan(plan_id) — activate plan ONLY after user confirms 'start'; sends tasks to all assigned agents",
            "- create_plan_task(plan_id, title, description) — create an UNASSIGNED task on the plan board",
            "- assign_plan_task(plan_id, task_id, agent_id) — assign a task to any agent, including yourself (use list_plan_assignees first to get valid IDs)",
            "- update_plan_task(plan_id, task_id, column_id?, title?, description?) — update a task's status or content (column_id changes only allowed on tasks assigned to you)",
            "- add_plan_artifact(plan_id, name, content, task_id?) — save outputs or summaries to the plan",
            "- list_plan_artifacts(plan_id, task_id?) — list all artifacts in a plan (optionally filtered by task)",
            "- get_plan_artifact(plan_id, artifact_id) — download and read artifact content",
            "- add_task_comment(plan_id, task_id, content) — PRIMARY way to communicate; use @agent_name to notify specific agents",
            "- list_task_comments(plan_id, task_id) — read comments on a task (check this before starting work)",
            "- a2a_discover() — list agents in your team for direct messaging (requires same team; may return empty)",
            "- a2a_call(target_agent_id, message) — send direct real-time message to another agent (use comments for async)",
        ]
    )
    return "\n".join(lines)


@router.get("/api/plans")
def list_plans(
    _: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
):
    return store.list_plans()


@router.post("/api/plans")
def create_plan(
    body: PlanCreate,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
):
    plan = store.create_plan(name=body.name, description=body.description)
    if caller.get("type") == "agent":
        store.assign_agent(plan.id, caller["agent_id"])
        plan.agent_ids = [caller["agent_id"]]
    return _plan_response(plan)


@router.get("/api/plans/{plan_id}")
def get_plan(
    plan_id: str,
    _: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
):
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return _plan_response(plan)


@router.put("/api/plans/{plan_id}")
def update_plan(
    plan_id: str,
    body: PlanUpdate,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
):
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    kwargs = body.model_dump(exclude_unset=True)
    updated = store.update_plan(plan_id, **kwargs)
    return _plan_response(updated)


@router.delete("/api/plans/{plan_id}")
def delete_plan(
    plan_id: str,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
    artifact_store: PlanArtifactStore = Depends(get_plan_artifact_store),
):
    if not store.delete_plan(plan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    artifact_store.delete_all_for_plan(plan_id)
    return {"ok": True}


@router.post("/api/plans/{plan_id}/tasks")
def add_task(
    plan_id: str,
    body: TaskCreate,
    _: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
):
    if not store.get_plan(plan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    task = store.add_task(
        plan_id,
        column_id=body.column_id,
        title=body.title,
        description=body.description,
        agent_id=body.agent_id,
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task"
        )
    return task.model_dump()


def _build_task_status_notification(plan, task, old_column_id: str) -> str:
    """Build a notification message when a task changes columns (status)."""
    old_col = next((c for c in plan.columns if c.id == old_column_id), None)
    new_col = next((c for c in plan.columns if c.id == task.column_id), None)
    old_label = old_col.title if old_col else old_column_id
    new_label = new_col.title if new_col else task.column_id
    assigned = f" (assigned to `{task.agent_id}`)" if task.agent_id else " (unassigned)"

    return (
        f"## Plan update: task status changed\n\n"
        f"**Plan:** {plan.name} (`{plan.id}`)\n"
        f"**Task:** {task.title} (`{task.id}`){assigned}\n"
        f"**Status:** {old_label} → **{new_label}**\n\n"
        f"{task.description[:200] if task.description else '(no description)'}\n\n"
        f"If this task is now assigned to you or in your queue, please review and continue working on it. "
        f'Use `get_plan(plan_id="{plan.id}")` to see the full plan board.'
    )


@router.put("/api/plans/{plan_id}/tasks/{task_id}")
async def update_task(
    plan_id: str,
    task_id: str,
    body: TaskUpdate,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
    activity_store=Depends(get_activity_events_store),
):
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if caller.get("type") == "user":
        pass
    else:
        require_plan_access(plan, caller)

    old_task = next((t for t in plan.tasks if t.id == task_id), None)
    old_column_id = old_task.column_id if old_task else None

    kwargs = body.model_dump(exclude_unset=True)

    # Agents can only change the status (column_id) of tasks assigned to them
    if caller.get("type") == "agent" and "column_id" in kwargs:
        caller_agent_id = caller.get("agent_id")
        if not old_task or old_task.agent_id != caller_agent_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agent can only change the status of tasks assigned to them",
            )

    # Task must have an assignee before its status can be changed
    if "column_id" in kwargs:
        effective_agent_id = kwargs.get("agent_id") or (old_task.agent_id if old_task else "")
        if not effective_agent_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Task must be assigned to an agent before its status can be changed",
            )

    task = store.update_task(plan_id, task_id, **kwargs)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # When a task is assigned to an agent, ensure that agent is in plan.agent_ids
    new_agent_id = kwargs.get("agent_id")
    newly_added_to_plan = False
    if new_agent_id and new_agent_id not in (plan.agent_ids or []):
        store.assign_agent(plan_id, new_agent_id)
        newly_added_to_plan = True

    # If the plan is active and a new agent was just added, send them their plan context
    if newly_added_to_plan and plan.status == "active":
        fresh_plan = store.get_plan(plan_id)
        if fresh_plan:
            plan_ctx = {
                "session_key": f"plan:{plan_id}",
                "plan_id": plan_id,
                "type": "plan_assigned",
                "channel": "admin",
                "chat_id": f"plan:{plan_id}",
            }
            try:
                await runtime.send_message(
                    new_agent_id,
                    _build_plan_context_message(fresh_plan, agent_id=new_agent_id),
                    context=plan_ctx,
                )
            except Exception as exc:
                logger.warning(
                    f"Failed to send plan context to newly assigned agent {new_agent_id}: {exc}"
                )

    column_changed = (
        old_column_id is not None and "column_id" in kwargs and kwargs["column_id"] != old_column_id
    )
    if column_changed:
        updated_plan = store.get_plan(plan_id)
        effective_plan = updated_plan or plan
        old_col = next((c for c in effective_plan.columns if c.id == old_column_id), None)
        new_col = next((c for c in effective_plan.columns if c.id == task.column_id), None)
        old_label = old_col.title if old_col else old_column_id
        new_label = new_col.title if new_col else task.column_id
        assigned_label = f" assigned to {task.agent_id}" if task.agent_id else ""
        activity_content = f"Task **{task.title}**{assigned_label}: {old_label} → {new_label}"

        # Emit activity event for every agent assigned to the plan (including agent that made the change)
        for aid in plan.agent_ids or []:
            try:
                ev = ActivityEvent(
                    agent_id=aid,
                    event_type="task_status_changed",
                    channel="admin",
                    content=activity_content,
                    plan_id=plan_id,
                )
                activity_store.insert(ev)
                runtime.emit_activity(aid, ev)
            except Exception as exc:
                logger.warning(f"Failed to emit task status activity for agent {aid}: {exc}")

        if plan.status == "active" and plan.agent_ids:
            message = _build_task_status_notification(effective_plan, task, old_column_id)
            caller_agent_id = caller.get("agent_id") if caller.get("type") == "agent" else None
            plan_ctx = {
                "session_key": f"plan:{plan_id}",
                "plan_id": plan_id,
                "task_id": task_id,
                "type": "task_status_changed",
                "channel": "admin",
                "chat_id": f"plan:{plan_id}",
            }
            for aid in plan.agent_ids:
                if aid == caller_agent_id:
                    continue
                try:
                    await runtime.send_message(aid, message, context=plan_ctx)
                except Exception as exc:
                    logger.warning(f"Failed to notify agent {aid} of task status change: {exc}")

    return task.model_dump()


@router.delete("/api/plans/{plan_id}/tasks/{task_id}")
def delete_task(
    plan_id: str,
    task_id: str,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
):
    if not store.get_plan(plan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if not store.delete_task(plan_id, task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"ok": True}


@router.get("/api/plans/{plan_id}/tasks/{task_id}/comments")
def list_task_comments(
    plan_id: str,
    task_id: str,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
):
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    if not any(t.id == task_id for t in plan.tasks):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    comments = store.list_comments(plan_id, task_id)
    return [c.model_dump() for c in comments]


_MENTION_PATTERN = _re.compile(r"@([a-zA-Z0-9_-]+)")


def _parse_mentions(content: str) -> list[str]:
    """Extract @mentions from comment content. Returns list of mentioned names/ids."""
    return _MENTION_PATTERN.findall(content)


@router.post("/api/plans/{plan_id}/tasks/{task_id}/comments")
async def add_task_comment(
    plan_id: str,
    task_id: str,
    body: CommentCreate,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    agent_store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
    activity_store=Depends(get_activity_events_store),
):
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    if caller.get("type") == "user":
        author_type = "admin"
        author_id = caller.get("id", "")
        author_name = caller.get("username", "Admin")
    else:
        author_type = "agent"
        author_id = caller.get("agent_id", "")
        agent = agent_store.get_agent(author_id) if author_id else None
        author_name = agent.name if agent else author_id or "Agent"

    content = body.content or ""
    comment = store.add_comment(
        plan_id,
        task_id,
        author_type=author_type,
        author_id=author_id,
        author_name=author_name,
        content=content,
    )
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Parse @mentions and notify mentioned agents
    mentions = _parse_mentions(content)
    if mentions and plan.status == "active" and plan.agent_ids:
        task = next((t for t in plan.tasks if t.id == task_id), None)
        task_title = task.title if task else task_id

        # Build a map of agent names/ids to agent objects
        agents_by_name: dict[str, str] = {}
        agents_by_id: dict[str, str] = {}
        for aid in plan.agent_ids:
            a = agent_store.get_agent(aid)
            if a:
                agents_by_id[aid] = aid
                if a.name:
                    agents_by_name[a.name.lower()] = aid
                    agents_by_name[a.name.lower().replace(" ", "_")] = aid
                    agents_by_name[a.name.lower().replace(" ", "-")] = aid

        # Resolve mentions to agent IDs
        mentioned_agent_ids: set[str] = set()
        for mention in mentions:
            mention_lower = mention.lower()
            if mention in agents_by_id:
                mentioned_agent_ids.add(mention)
            elif mention_lower in agents_by_name:
                mentioned_agent_ids.add(agents_by_name[mention_lower])

        # Send notifications to mentioned agents (skip the author)
        for aid in mentioned_agent_ids:
            if aid == author_id:
                continue
            try:
                runtime_status = await runtime.get_status(aid)
                if runtime_status.status != "running":
                    continue
                notification = (
                    f"**@mention** from {author_name} on task `{task_title}`:\n\n"
                    f"> {content}\n\n"
                    f"Plan: {plan.name} (id=`{plan.id}`)\n"
                    f"Task: `{task_id}`"
                )
                await runtime.send_message(
                    aid,
                    notification,
                    context={
                        "session_key": f"plan:{plan_id}",
                        "plan_id": plan_id,
                        "task_id": task_id,
                        "type": "mention",
                        "channel": "admin",
                        "chat_id": f"plan:{plan_id}",
                    },
                )
            except Exception as exc:
                logger.warning(f"Failed to notify agent {aid} of mention: {exc}")

    # Emit activity event so the comment appears in every assigned agent's timeline
    comment_preview = content[:200] + "…" if len(content) > 200 else content
    task_obj = next((t for t in plan.tasks if t.id == task_id), None)
    task_title = task_obj.title if task_obj else task_id
    for aid in plan.agent_ids or []:
        try:
            ev = ActivityEvent(
                agent_id=author_id or aid,
                event_type="task_comment",
                channel="admin",
                content=f"**{author_name}** on *{task_title}*: {comment_preview}",
                plan_id=plan_id,
            )
            activity_store.insert(ev)
            runtime.emit_activity(aid, ev)
        except Exception as exc:
            logger.warning(f"Failed to emit comment activity for agent {aid}: {exc}")

    return comment.model_dump()


@router.delete("/api/plans/{plan_id}/comments/{comment_id}")
def delete_task_comment(
    plan_id: str,
    comment_id: str,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
):
    if not store.get_plan(plan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if not store.delete_comment(plan_id, comment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return {"ok": True}


@router.get("/api/plans/{plan_id}/assignees")
async def list_plan_assignees(
    plan_id: str,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    agent_store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """List all agents available for assignment to this plan.

    Returns every agent with their id, name, description, running status,
    and whether they are already assigned to the plan. Agents and admin users
    can call this endpoint.
    """
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)

    # Exclude the calling agent from the assignees list. The coordinator (the
    # agent managing the plan) should not appear as a valid task assignee —
    # their role is to plan and delegate, not to own tasks on the board.
    caller_agent_id = caller.get("agent_id") if caller.get("type") == "agent" else None

    all_agents = agent_store.list_agents()
    assigned_ids = set(plan.agent_ids or [])
    result = []
    for a in all_agents:
        if caller_agent_id and a.id == caller_agent_id:
            continue
        runtime_status = await runtime.get_status(a.id)
        result.append(
            {
                "id": a.id,
                "name": a.name or a.id,
                "description": a.description or "",
                "status": runtime_status.status,
                "assigned": a.id in assigned_ids,
            }
        )
    return result


@router.post("/api/plans/{plan_id}/agents/{agent_id}")
def assign_agent(
    plan_id: str,
    agent_id: str,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
    agent_store: AgentStore = Depends(get_agent_store),
):
    if not store.get_plan(plan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if not agent_store.get_agent(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    store.assign_agent(plan_id, agent_id)
    return {"ok": True}


@router.delete("/api/plans/{plan_id}/agents/{agent_id}")
def remove_agent(
    plan_id: str,
    agent_id: str,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
):
    if not store.get_plan(plan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    store.remove_agent(plan_id, agent_id)
    return {"ok": True}


class AssistantRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_id: str
    message: str


@router.post("/api/plans/{plan_id}/assistant")
async def plan_assistant(
    plan_id: str,
    body: AssistantRequest,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
    agent_store: AgentStore = Depends(get_agent_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Send a planning request to a running agent.

    The agent uses its own LLM + plan tools (create_plan_task, update_plan_task,
    etc.) to break down the request and manage the plan board.
    Auto-assigns the assistant agent to the plan so it has API access.
    """
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    agent = agent_store.get_agent(body.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if body.agent_id not in (plan.agent_ids or []):
        store.assign_agent(plan_id, body.agent_id)
        plan = store.get_plan(plan_id)

    all_agents = agent_store.list_agents()
    agents_info = [f"- {a.name or a.id} (id=`{a.id}`)" for a in all_agents]
    agents_section = "\n".join(agents_info) if agents_info else "  (none)"

    plan_context = _build_plan_context_message(plan, agent_id=body.agent_id)
    prompt = (
        f"{plan_context}\n\n"
        f"## Agents available for assignment\n"
        f"{agents_section}\n\n"
        f"---\n\n"
        f"## Planning request\n"
        f"{body.message}\n\n"
        f"**You are in Planning mode.** Follow these steps in order — do NOT skip ahead:\n\n"
        f"**Step 1 — Clarify**\n"
        f"Identify what is unclear. Ask the user up to 3 focused questions "
        f"(scope, goals, constraints, priorities, expected outputs). Wait for answers.\n\n"
        f"**Step 2 — Propose task breakdown**\n"
        f"Write out the full task list in plain text: title, what needs to be done, "
        f"and what agent capability is needed. Agents can handle multiple tasks; assign based on best fit and consider workload.\n"
        f'Ask the user: "Does this look right?"\n\n'
        f"**Step 3 — Create tasks (unassigned)**\n"
        f"After the user approves the task list:\n"
        f"- Call `create_plan_task(plan_id, title, description)` for EACH task — do NOT set agent_id yet.\n"
        f"- Tasks are created unassigned so the user can see them on the board first.\n\n"
        f"**Step 4 — Assign agents**\n"
        f"Call `list_plan_assignees(plan_id='{plan.id}')` to see ALL available agents and their descriptions.\n"
        f"ONLY use agent IDs from this list — never guess or invent IDs.\n"
        f"Match each task to the best-suited agent, then call `assign_plan_task(plan_id, task_id, agent_id)` for each.\n"
        f'Show the user a summary of assignments and ask: "Should I start the plan?"\n\n'
        f"**Step 5 — Activate (only after user confirms 'start')**\n"
        f"ONLY when the user explicitly says yes/start/go:\n"
        f"- Call `activate_plan(plan_id='{plan.id}')` — marks the plan ready. Running agents receive context; you decide when to engage others via the plan assistant.\n\n"
        f"Do NOT call `activate_plan` until the user confirms."
    )

    response = await runtime.send_message(
        body.agent_id,
        prompt,
        context={
            "session_key": f"plan:{plan_id}",
            "plan_id": plan_id,
            "type": "plan_assistant",
            "channel": "admin",
            "chat_id": f"plan:{plan_id}",
        },
    )
    return {"ok": True, "agent_id": body.agent_id, "response": response or "Request sent to agent."}


@router.post("/api/plans/{plan_id}/activate")
async def activate_plan(
    plan_id: str,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Mark plan active and send context to running agents. Coordinator decides when to engage others via plan assistant. Does NOT require all agents to be running."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)

    agent_ids = plan.agent_ids or []

    unassigned_tasks = [t for t in (plan.tasks or []) if not t.agent_id]
    if unassigned_tasks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "unassigned_tasks",
                "tasks": [{"id": t.id, "title": t.title} for t in unassigned_tasks],
                "message": f"{len(unassigned_tasks)} task(s) have no assignee. Assign all tasks before activating.",
            },
        )

    store.update_plan(plan_id, status="active")
    active_plan = store.get_plan(plan_id)

    for aid in agent_ids:
        runtime_status = await runtime.get_status(aid)
        if runtime_status.status != "running":
            continue
        message = _build_plan_context_message(active_plan or plan, agent_id=aid)
        try:
            await runtime.send_message(
                aid,
                message,
                context={
                    "session_key": f"plan:{plan_id}",
                    "plan_id": plan_id,
                    "channel": "admin",
                    "chat_id": f"plan:{plan_id}",
                },
            )
        except Exception as exc:
            logger.warning(f"Failed to send plan context to agent {aid}: {exc}")

    return {"ok": True, "status": "active"}


@router.post("/api/plans/{plan_id}/deactivate")
async def deactivate_plan(
    plan_id: str,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Notify agents that the plan is paused. Plan status becomes paused. Does NOT stop agents."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    await runtime.deactivate_plan(plan_id, plan.agent_ids or [])
    store.update_plan(plan_id, status="paused")
    return {"ok": True, "status": "paused"}


@router.post("/api/plans/{plan_id}/complete")
async def complete_plan(
    plan_id: str,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
    runtime: AgentRuntimeBackend = Depends(get_runtime),
):
    """Mark a plan as completed. Notifies all assigned agents. Does NOT stop agents."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    await runtime.complete_plan(plan_id, plan.name, plan.agent_ids or [])
    store.update_plan(plan_id, status="completed")
    return {"ok": True, "status": "completed"}


@router.post("/api/plans/{plan_id}/artifacts")
def add_artifact(
    plan_id: str,
    body: ArtifactCreate,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    artifact_store: PlanArtifactStore = Depends(get_plan_artifact_store),
):
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    artifact = artifact_store.add(
        plan_id,
        name=body.name or "artifact",
        content=body.content,
        task_id=body.task_id or "",
        content_type=body.content_type or "text/plain",
    )
    return artifact


@router.get("/api/plans/{plan_id}/artifacts")
def list_artifacts(
    plan_id: str,
    task_id: str | None = None,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    artifact_store: PlanArtifactStore = Depends(get_plan_artifact_store),
):
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    return artifact_store.list_artifacts(plan_id, task_id=task_id)


@router.get("/api/plans/{plan_id}/artifacts/{artifact_id}")
def get_artifact(
    plan_id: str,
    artifact_id: str,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    artifact_store: PlanArtifactStore = Depends(get_plan_artifact_store),
):
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    artifact = artifact_store.get_artifact(plan_id, artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return artifact


MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/api/plans/{plan_id}/artifacts/upload")
async def upload_artifact(
    plan_id: str,
    file: UploadFile,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
    artifact_store: PlanArtifactStore = Depends(get_plan_artifact_store),
):
    """Upload a file as a plan artifact (drag-drop from the frontend)."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {MAX_UPLOAD_SIZE // (1024 * 1024)} MB)",
        )
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "uploaded_file"
    artifact = artifact_store.add_file(
        plan_id,
        name=filename,
        data=data,
        content_type=content_type,
    )
    return artifact


@router.get("/api/plans/{plan_id}/artifacts/{artifact_id}/download")
def download_artifact(
    plan_id: str,
    artifact_id: str,
    caller: dict = Depends(get_user_or_agent),
    store: PlanStore = Depends(get_plan_store),
    artifact_store: PlanArtifactStore = Depends(get_plan_artifact_store),
):
    """Download a plan artifact file."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    require_plan_access(plan, caller)
    result = artifact_store.read_file(plan_id, artifact_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    meta, data = result
    ct = meta.get("content_type", "application/octet-stream")
    filename = meta.get("name", "file")
    return Response(
        content=data,
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/api/plans/{plan_id}/artifacts/{artifact_id}")
def delete_artifact(
    plan_id: str,
    artifact_id: str,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
    artifact_store: PlanArtifactStore = Depends(get_plan_artifact_store),
):
    """Delete a single plan artifact."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if not artifact_store.delete_artifact(plan_id, artifact_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return {"ok": True}


@router.post("/api/plans/{plan_id}/artifacts/{artifact_id}/rename")
def rename_artifact(
    plan_id: str,
    artifact_id: str,
    body: ArtifactRename,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
    artifact_store: PlanArtifactStore = Depends(get_plan_artifact_store),
):
    """Rename a plan artifact."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if not body.new_name or "/" in body.new_name or ".." in body.new_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid new name")
    artifact = artifact_store.rename_artifact(plan_id, artifact_id, body.new_name)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found or rename failed"
        )
    return artifact


@router.post("/api/plans/{plan_id}/artifacts/{artifact_id}/move")
def move_artifact(
    plan_id: str,
    artifact_id: str,
    body: ArtifactMove,
    _: dict = Depends(get_current_user),
    store: PlanStore = Depends(get_plan_store),
    artifact_store: PlanArtifactStore = Depends(get_plan_artifact_store),
):
    """Move a plan artifact to a different task (or no task)."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if body.task_id and not any(t.id == body.task_id for t in plan.tasks):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Task not found in plan"
        )
    artifact = artifact_store.move_artifact(plan_id, artifact_id, body.task_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return artifact


@router.get("/api/plans/{plan_id}/logs")
async def plan_logs(
    request: Request,
    plan_id: str,
    store: PlanStore = Depends(get_plan_store),
    activity_store=Depends(get_activity_events_store),
):
    """SSE stream aggregating activity from all agents assigned to a plan.

    Uses the DB-backed ActivityEventsStore (same source of truth as agent logs)
    so events are available regardless of whether agents are currently connected.
    """
    token = request.query_params.get("token") or (
        request.headers.get("Authorization") or ""
    ).replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    # Accept short-lived stream token (from api.auth.streamToken()) or JWT
    payload = verify_stream_token(token) or decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    agent_ids = plan.agent_ids or []

    def _event_data(row: dict) -> dict:
        data: dict = {
            "agent_id": row.get("agent_id", ""),
            "timestamp": row.get("timestamp", ""),
            "event_type": row.get("event_type", ""),
            "channel": row.get("channel", ""),
            "content": row.get("content", ""),
        }
        if row.get("tool_name") is not None:
            data["tool_name"] = row["tool_name"]
        if row.get("result_status") is not None:
            data["result_status"] = row["result_status"]
        if row.get("duration_ms") is not None:
            data["duration_ms"] = row["duration_ms"]
        return {"event": "message", "data": json.dumps(data)}

    async def event_stream():
        try:
            yield {"event": "ping", "data": ""}

            backlog = activity_store.get_recent_for_plan(plan_id, agent_ids, limit=200)
            for row in backlog:
                yield _event_data(row)
            last_id = max((r["id"] for r in backlog), default=None)

            while True:
                await asyncio.sleep(_PLAN_LOG_POLL_INTERVAL)
                new_rows = activity_store.get_recent_for_plan(
                    plan_id, agent_ids, limit=50, after_id=last_id
                )
                for row in new_rows:
                    yield _event_data(row)
                    last_id = row["id"]
                yield {"event": "ping", "data": ""}
        except (asyncio.CancelledError, GeneratorExit):
            return

    return EventSourceResponse(event_stream(), ping=20)
