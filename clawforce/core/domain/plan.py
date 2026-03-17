"""Plan, task, and column data models."""

import uuid
from datetime import datetime, timezone

from pydantic import Field

from clawforce.core.domain.agent import Base


class PlanTask(Base):
    """A single task on a plan board."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    column_id: str = ""
    agent_id: str = ""
    position: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PlanColumn(Base):
    """A column on a plan Kanban board."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    position: int = 0


class TaskComment(Base):
    """A comment on a plan task (human or agent)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    author_type: str = ""  # "admin" or "agent"
    author_id: str = ""
    author_name: str = ""
    content: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _default_plan_columns(plan_id: str | None = None) -> list[PlanColumn]:
    """Default Kanban columns: Todo, In Progress, Blocked, Done.

    If plan_id is provided, column IDs are prefixed with the plan ID to ensure uniqueness.
    """
    prefix = f"{plan_id}-" if plan_id else ""
    return [
        PlanColumn(id=f"{prefix}col-todo", title="Todo", position=0),
        PlanColumn(id=f"{prefix}col-in-progress", title="In Progress", position=1),
        PlanColumn(id=f"{prefix}col-blocked", title="Blocked", position=2),
        PlanColumn(id=f"{prefix}col-done", title="Done", position=3),
    ]


class PlanDef(Base):
    """A plan with Kanban columns and tasks. Agents assigned collaborate via shared workspace.

    Status lifecycle: draft -> active -> (paused | completed).
    - draft: Created, not yet activated. Use activate to start.
    - active: Running. Assigned agents receive context and work on tasks.
    - paused: Admin paused the plan. Agents should stop working on it until re-activated.
    - completed: Plan finished.

    Capabilities:
    - Agent (assigned to plan): create plans (auto-assigned), read plans, activate plans,
      create/update tasks, add/read artifacts. Cannot: pause plans, assign/remove agents,
      delete plans/tasks/artifacts, update plan metadata.
    - Admin: full control (activate, deactivate, assign agents, delete, etc.).
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: str = "draft"
    columns: list[PlanColumn] = Field(default_factory=_default_plan_columns)
    tasks: list[PlanTask] = Field(default_factory=list)
    agent_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
