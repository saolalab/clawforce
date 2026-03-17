"""Tests for clawforce.core.domain.runtime module."""

import pytest

from clawforce.core.domain.runtime import (
    AgentRuntimeBackend,
    AgentRuntimeError,
    AgentStatus,
)


class TestAgentStatus:
    """Tests for AgentStatus dataclass."""

    def test_create_basic(self):
        """AgentStatus should create with required fields."""
        status = AgentStatus(agent_id="agent-1", status="running")
        assert status.agent_id == "agent-1"
        assert status.status == "running"
        assert status.message == ""

    def test_create_with_message(self):
        """AgentStatus should accept message."""
        status = AgentStatus(
            agent_id="agent-1",
            status="failed",
            message="Connection failed",
        )
        assert status.message == "Connection failed"

    def test_create_with_mcp(self):
        """AgentStatus should accept mcp dict."""
        status = AgentStatus(
            agent_id="agent-1",
            status="running",
            mcp={"url": "http://localhost:8000", "tools": ["exec"]},
        )
        assert status.mcp == {"url": "http://localhost:8000", "tools": ["exec"]}

    def test_mcp_default_none(self):
        """AgentStatus mcp should default to None."""
        status = AgentStatus(agent_id="agent-1", status="running")
        assert status.mcp is None

    def test_status_values(self):
        """AgentStatus should support common status values."""
        for s in ["stopped", "running", "failed"]:
            status = AgentStatus(agent_id="a", status=s)
            assert status.status == s


class TestAgentRuntimeError:
    """Tests for AgentRuntimeError exception."""

    def test_raise_and_catch(self):
        """AgentRuntimeError should be raisable and catchable."""
        with pytest.raises(AgentRuntimeError) as exc_info:
            raise AgentRuntimeError("Agent not found")
        assert str(exc_info.value) == "Agent not found"

    def test_is_exception_subclass(self):
        """AgentRuntimeError should be Exception subclass."""
        assert issubclass(AgentRuntimeError, Exception)


class MockRuntimeBackend(AgentRuntimeBackend):
    """Mock implementation for testing base class."""

    def __init__(self):
        self.started_agents = set()
        self.messages_sent = []

    async def start_agent(self, agent_id: str) -> None:
        self.started_agents.add(agent_id)

    async def stop_agent(self, agent_id: str) -> None:
        self.started_agents.discard(agent_id)

    async def get_status(self, agent_id: str) -> AgentStatus:
        status = "running" if agent_id in self.started_agents else "stopped"
        return AgentStatus(agent_id=agent_id, status=status)

    async def send_message(
        self,
        agent_id: str,
        message: str,
        context: dict | None = None,
    ) -> str:
        self.messages_sent.append(
            {
                "agent_id": agent_id,
                "message": message,
                "context": context,
            }
        )
        return "ok"


class TestAgentRuntimeBackendABC:
    """Tests for AgentRuntimeBackend abstract base class."""

    def test_cannot_instantiate_directly(self):
        """AgentRuntimeBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AgentRuntimeBackend()

    @pytest.mark.asyncio
    async def test_mock_start_stop(self):
        """Mock runtime should track started/stopped agents."""
        runtime = MockRuntimeBackend()

        await runtime.start_agent("agent-1")
        assert "agent-1" in runtime.started_agents

        await runtime.stop_agent("agent-1")
        assert "agent-1" not in runtime.started_agents

    @pytest.mark.asyncio
    async def test_mock_get_status(self):
        """Mock runtime should return correct status."""
        runtime = MockRuntimeBackend()

        status = await runtime.get_status("agent-1")
        assert status.status == "stopped"

        await runtime.start_agent("agent-1")
        status = await runtime.get_status("agent-1")
        assert status.status == "running"

    @pytest.mark.asyncio
    async def test_mock_send_message(self):
        """Mock runtime should track sent messages."""
        runtime = MockRuntimeBackend()

        result = await runtime.send_message(
            "agent-1",
            "Hello agent",
            context={"session_key": "test"},
        )

        assert result == "ok"
        assert len(runtime.messages_sent) == 1
        assert runtime.messages_sent[0]["agent_id"] == "agent-1"
        assert runtime.messages_sent[0]["message"] == "Hello agent"


class TestRuntimeBackendDefaultMethods:
    """Tests for default implementations in AgentRuntimeBackend."""

    @pytest.mark.asyncio
    async def test_subscribe_activity_empty(self):
        """Default subscribe_activity should return empty iterator."""
        runtime = MockRuntimeBackend()
        iterator = runtime.subscribe_activity("agent-1")

        events = []
        async for event in iterator:
            events.append(event)

        assert events == []

    def test_get_recent_activity_empty(self):
        """Default get_recent_activity should return empty list."""
        runtime = MockRuntimeBackend()
        events = runtime.get_recent_activity("agent-1")
        assert events == []

    @pytest.mark.asyncio
    async def test_list_workspace_empty(self):
        """Default list_workspace should return empty list."""
        runtime = MockRuntimeBackend()
        files = await runtime.list_workspace("agent-1")
        assert files == []

    @pytest.mark.asyncio
    async def test_read_workspace_file_none(self):
        """Default read_workspace_file should return None."""
        runtime = MockRuntimeBackend()
        content = await runtime.read_workspace_file("agent-1", "file.txt")
        assert content is None

    @pytest.mark.asyncio
    async def test_write_workspace_file_false(self):
        """Default write_workspace_file should return False."""
        runtime = MockRuntimeBackend()
        result = await runtime.write_workspace_file("agent-1", "file.txt", "content")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_profile_empty(self):
        """Default list_profile should return empty list."""
        runtime = MockRuntimeBackend()
        files = await runtime.list_profile("agent-1")
        assert files == []

    @pytest.mark.asyncio
    async def test_read_profile_file_none(self):
        """Default read_profile_file should return None."""
        runtime = MockRuntimeBackend()
        content = await runtime.read_profile_file("agent-1", "AGENTS.md")
        assert content is None

    @pytest.mark.asyncio
    async def test_write_profile_file_false(self):
        """Default write_profile_file should return False."""
        runtime = MockRuntimeBackend()
        result = await runtime.write_profile_file("agent-1", "AGENTS.md", "# Agent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_config_none(self):
        """Default get_config should return None."""
        runtime = MockRuntimeBackend()
        config = await runtime.get_config("agent-1")
        assert config is None

    @pytest.mark.asyncio
    async def test_update_config_none(self):
        """Default update_config should return None."""
        runtime = MockRuntimeBackend()
        config = await runtime.update_config("agent-1", {"key": "value"})
        assert config is None

    @pytest.mark.asyncio
    async def test_apply_config_none(self):
        """Default apply_config should return None (agent offline)."""
        runtime = MockRuntimeBackend()
        config = await runtime.apply_config("agent-1", {"key": "value"})
        assert config is None

    @pytest.mark.asyncio
    async def test_install_skill_raises(self):
        """Default install_skill should raise AgentRuntimeError."""
        runtime = MockRuntimeBackend()
        with pytest.raises(AgentRuntimeError, match="not implemented"):
            await runtime.install_skill("agent-1", "test-skill")

    @pytest.mark.asyncio
    async def test_uninstall_skill_raises(self):
        """Default uninstall_skill should raise AgentRuntimeError."""
        runtime = MockRuntimeBackend()
        with pytest.raises(AgentRuntimeError, match="not implemented"):
            await runtime.uninstall_skill("agent-1", "test-skill")


class TestRuntimePlanActivation:
    """Tests for plan activation methods."""

    @pytest.mark.asyncio
    async def test_activate_plan_running_agent(self):
        """activate_plan should send context to running agents."""
        runtime = MockRuntimeBackend()
        await runtime.start_agent("agent-1")

        results = await runtime.activate_plan(
            plan_id="plan-1",
            agent_ids=["agent-1"],
            plan_context_message="Start working on plan",
        )

        assert results["agent-1"]["ok"] is True
        assert len(runtime.messages_sent) == 1
        assert runtime.messages_sent[0]["message"] == "Start working on plan"
        assert runtime.messages_sent[0]["context"]["plan_id"] == "plan-1"

    @pytest.mark.asyncio
    async def test_activate_plan_stopped_agent(self):
        """activate_plan should report error for stopped agents."""
        runtime = MockRuntimeBackend()

        results = await runtime.activate_plan(
            plan_id="plan-1",
            agent_ids=["agent-stopped"],
            plan_context_message="Start working",
        )

        assert results["agent-stopped"]["ok"] is False
        assert results["agent-stopped"]["error"] == "not_running"

    @pytest.mark.asyncio
    async def test_deactivate_plan(self):
        """deactivate_plan should notify agents."""
        runtime = MockRuntimeBackend()
        await runtime.start_agent("agent-1")

        await runtime.deactivate_plan(
            plan_id="plan-1",
            agent_ids=["agent-1"],
        )

        assert len(runtime.messages_sent) == 1
        assert "paused" in runtime.messages_sent[0]["message"]


class TestRuntimeTerminalMethods:
    """Tests for terminal-related methods."""

    def test_supports_terminal_default(self):
        """Default supports_terminal should return False."""
        runtime = MockRuntimeBackend()
        assert runtime.supports_terminal() is False

    def test_get_terminal_target_default(self):
        """Default get_terminal_target should return None."""
        runtime = MockRuntimeBackend()
        assert runtime.get_terminal_target("agent-1") is None


class TestRuntimeSoftwareMethods:
    """Tests for software install/uninstall methods."""

    @pytest.mark.asyncio
    async def test_install_software_raises(self):
        """Default install_software should raise AgentRuntimeError."""
        runtime = MockRuntimeBackend()
        with pytest.raises(AgentRuntimeError, match="not implemented"):
            await runtime.install_software(
                agent_id="agent-1",
                slug="eslint",
                package="eslint",
                install_type="npm",
            )

    @pytest.mark.asyncio
    async def test_uninstall_software_raises(self):
        """Default uninstall_software should raise AgentRuntimeError."""
        runtime = MockRuntimeBackend()
        with pytest.raises(AgentRuntimeError, match="not implemented"):
            await runtime.uninstall_software("agent-1", "eslint")
