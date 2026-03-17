"""Tests for clawforce.core.domain module."""

import uuid

from clawforce.core.domain.agent import AgentDef, UserDef
from clawforce.core.domain.plan import (
    PlanColumn,
    PlanDef,
    PlanTask,
    _default_plan_columns,
)


class TestAgentDef:
    """Tests for AgentDef model."""

    def test_defaults(self):
        """AgentDef should have correct defaults."""
        agent = AgentDef()
        assert agent.id is not None
        assert uuid.UUID(agent.id)
        assert agent.name == ""
        assert agent.enabled is True
        assert agent.status == "stopped"
        assert agent.mode == ""
        assert agent.created_at is not None

    def test_custom_values(self):
        """AgentDef should accept custom values."""
        agent = AgentDef(
            id="custom-id",
            name="Agent Smith",
            description="Test agent",
            enabled=False,
            status="running",
        )
        assert agent.id == "custom-id"
        assert agent.name == "Agent Smith"
        assert agent.enabled is False
        assert agent.status == "running"

    def test_base_path_auto_set(self):
        """base_path should default to agent id if not set."""
        agent = AgentDef(id="agent-123")
        assert agent.base_path == "agent-123"

    def test_base_path_preserved_if_set(self):
        """Explicit base_path should be preserved."""
        agent = AgentDef(id="agent-123", base_path="custom/path")
        assert agent.base_path == "custom/path"

    def test_camel_case_parsing(self):
        """AgentDef should accept snake_case keys."""
        agent = AgentDef.model_validate(
            {
                "owner_id": "user-1",
                "base_path": "custom-path",
            }
        )
        assert agent.base_path == "custom-path"


class TestUserDef:
    """Tests for UserDef model."""

    def test_defaults(self):
        """UserDef should have correct defaults."""
        user = UserDef()
        assert user.id is not None
        assert user.username == ""
        assert user.password_hash == ""
        assert user.role == "admin"
        assert user.created_at is not None

    def test_custom_values(self):
        """UserDef should accept custom values."""
        user = UserDef(
            username="admin",
            password_hash="hashed_password",
            role="super_admin",
        )
        assert user.username == "admin"
        assert user.password_hash == "hashed_password"
        assert user.role == "super_admin"


class TestPlanColumn:
    """Tests for PlanColumn model."""

    def test_defaults(self):
        """PlanColumn should have correct defaults."""
        col = PlanColumn()
        assert col.id is not None
        assert col.title == ""
        assert col.position == 0

    def test_custom_values(self):
        """PlanColumn should accept custom values."""
        col = PlanColumn(
            id="col-1",
            title="In Progress",
            position=1,
        )
        assert col.id == "col-1"
        assert col.title == "In Progress"
        assert col.position == 1


class TestPlanTask:
    """Tests for PlanTask model."""

    def test_defaults(self):
        """PlanTask should have correct defaults."""
        task = PlanTask()
        assert task.id is not None
        assert task.title == ""
        assert task.description == ""
        assert task.column_id == ""
        assert task.agent_id == ""
        assert task.position == 0

    def test_custom_values(self):
        """PlanTask should accept custom values."""
        task = PlanTask(
            id="task-1",
            title="Implement feature X",
            description="Build the new feature",
            column_id="col-in-progress",
            agent_id="agent-1",
            position=2,
        )
        assert task.id == "task-1"
        assert task.title == "Implement feature X"
        assert task.column_id == "col-in-progress"
        assert task.agent_id == "agent-1"


class TestDefaultPlanColumns:
    """Tests for _default_plan_columns helper."""

    def test_returns_four_columns(self):
        """Should return Todo, In Progress, Blocked, Done columns."""
        cols = _default_plan_columns()
        assert len(cols) == 4
        assert cols[0].title == "Todo"
        assert cols[1].title == "In Progress"
        assert cols[2].title == "Blocked"
        assert cols[3].title == "Done"

    def test_positions_are_sequential(self):
        """Column positions should be sequential."""
        cols = _default_plan_columns()
        assert cols[0].position == 0
        assert cols[1].position == 1
        assert cols[2].position == 2
        assert cols[3].position == 3


class TestPlanDef:
    """Tests for PlanDef model."""

    def test_defaults(self):
        """PlanDef should have correct defaults."""
        plan = PlanDef()
        assert plan.id is not None
        assert plan.name == ""
        assert plan.status == "draft"
        assert len(plan.columns) == 4
        assert plan.tasks == []
        assert plan.agent_ids == []

    def test_custom_values(self):
        """PlanDef should accept custom values."""
        plan = PlanDef(
            id="plan-1",
            name="Project Alpha",
            description="New project plan",
            status="active",
            agent_ids=["agent-1", "agent-2"],
        )
        assert plan.id == "plan-1"
        assert plan.name == "Project Alpha"
        assert plan.status == "active"
        assert plan.agent_ids == ["agent-1", "agent-2"]

    def test_with_tasks(self):
        """PlanDef should accept tasks list."""
        tasks = [
            PlanTask(title="Task 1", column_id="col-todo"),
            PlanTask(title="Task 2", column_id="col-in-progress"),
        ]
        plan = PlanDef(tasks=tasks)
        assert len(plan.tasks) == 2
        assert plan.tasks[0].title == "Task 1"

    def test_with_custom_columns(self):
        """PlanDef should accept custom columns."""
        cols = [
            PlanColumn(title="Backlog", position=0),
            PlanColumn(title="Active", position=1),
            PlanColumn(title="Review", position=2),
            PlanColumn(title="Done", position=3),
        ]
        plan = PlanDef(columns=cols)
        assert len(plan.columns) == 4
        assert plan.columns[2].title == "Review"
