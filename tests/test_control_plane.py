"""Tests for control_plane_overrides (clawforce.core.domain.agent)."""

from clawforce.core.domain.agent import AgentDef, control_plane_overrides


class TestControlPlaneOverrides:
    def test_returns_expected_keys(self):
        agent = AgentDef(id="agent-123", agent_token="tok-abc")
        cp = control_plane_overrides(agent)
        assert "admin_url" in cp
        assert "agent_id" in cp
        assert "agent_token" in cp
        assert "heartbeat_interval" in cp

    def test_agent_id_and_token_preserved(self):
        agent = AgentDef(id="my-agent", agent_token="secret-token")
        cp = control_plane_overrides(agent)
        assert cp["agent_id"] == "my-agent"
        assert cp["agent_token"] == "secret-token"

    def test_empty_token_ok(self):
        agent = AgentDef(id="a1", agent_token="")
        cp = control_plane_overrides(agent)
        assert cp["agent_token"] == ""

    def test_heartbeat_interval_default(self):
        agent = AgentDef(id="a1")
        cp = control_plane_overrides(agent)
        assert cp["heartbeat_interval"] == 30

    def test_admin_url_from_env(self, monkeypatch):
        monkeypatch.setenv("ADMIN_PUBLIC_URL", "https://admin.example.com")
        agent = AgentDef(id="a1")
        cp = control_plane_overrides(agent)
        assert cp["admin_url"] == "https://admin.example.com"
