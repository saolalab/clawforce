"""Tests for crud._build_update_overrides."""

from clawforce.apis.agents.crud import _build_update_overrides


class TestBuildUpdateOverrides:
    def test_empty_when_all_none(self):
        assert _build_update_overrides() == {}

    def test_model_only(self):
        result = _build_update_overrides(model="gpt-4")
        assert result == {"agents": {"defaults": {"model": "gpt-4"}}}

    def test_multiple_agent_defaults(self):
        result = _build_update_overrides(
            model="claude-3",
            temperature=0.5,
            max_tokens=4096,
        )
        assert result["agents"]["defaults"]["model"] == "claude-3"
        assert result["agents"]["defaults"]["temperature"] == 0.5
        assert result["agents"]["defaults"]["max_tokens"] == 4096

    def test_channels_override(self):
        channels = {"telegram": {"enabled": True}}
        result = _build_update_overrides(channels=channels)
        assert "channels" in result
        assert result["channels"]["telegram"]["enabled"] is True

    def test_providers_override(self):
        providers = {"openai": {"api_key": "sk-xxx"}}
        result = _build_update_overrides(providers=providers)
        assert result == {"providers": providers}

    def test_tools_override(self):
        tools = {"shell": {"enabled": True}}
        result = _build_update_overrides(tools=tools)
        assert result == {"tools": tools}

    def test_skills_override(self):
        skills = {"skill-a": {"enabled": True}}
        result = _build_update_overrides(skills=skills)
        assert result == {"skills": skills}

    def test_fault_tolerance_in_defaults(self):
        ft = {"max_retries": 3}
        result = _build_update_overrides(fault_tolerance=ft)
        assert result["agents"]["defaults"]["fault_tolerance"] == ft

    def test_partial_omits_none(self):
        result = _build_update_overrides(
            model="gpt-4",
            temperature=None,
            channels={"slack": {"enabled": True}},
        )
        assert "temperature" not in result.get("agents", {}).get("defaults", {})
        assert result["channels"]["slack"]["enabled"] is True
