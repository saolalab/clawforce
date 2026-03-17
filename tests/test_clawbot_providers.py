"""Tests for clawbot.providers module."""

import pytest

from clawbot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class TestToolCallRequest:
    """Tests for ToolCallRequest dataclass."""

    def test_create(self):
        """ToolCallRequest should create with all fields."""
        req = ToolCallRequest(
            id="call_123",
            name="read_file",
            arguments={"path": "/test.txt"},
        )
        assert req.id == "call_123"
        assert req.name == "read_file"
        assert req.arguments == {"path": "/test.txt"}


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_create_basic(self):
        """LLMResponse should create with minimal fields."""
        resp = LLMResponse(content="Hello!")
        assert resp.content == "Hello!"
        assert resp.tool_calls == []
        assert resp.finish_reason == "stop"
        assert resp.usage == {}
        assert resp.reasoning_content is None

    def test_create_with_tool_calls(self):
        """LLMResponse should accept tool calls."""
        tool_call = ToolCallRequest(id="1", name="test", arguments={})
        resp = LLMResponse(
            content=None,
            tool_calls=[tool_call],
            finish_reason="tool_calls",
        )
        assert resp.content is None
        assert len(resp.tool_calls) == 1
        assert resp.finish_reason == "tool_calls"

    def test_create_with_usage(self):
        """LLMResponse should accept usage stats."""
        resp = LLMResponse(
            content="Response",
            usage={"prompt_tokens": 100, "completion_tokens": 50},
        )
        assert resp.usage["prompt_tokens"] == 100
        assert resp.usage["completion_tokens"] == 50

    def test_create_with_reasoning(self):
        """LLMResponse should accept reasoning content."""
        resp = LLMResponse(
            content="Answer",
            reasoning_content="Let me think about this...",
        )
        assert resp.reasoning_content == "Let me think about this..."

    def test_has_tool_calls_true(self):
        """has_tool_calls should return True when tool calls present."""
        tool_call = ToolCallRequest(id="1", name="test", arguments={})
        resp = LLMResponse(content=None, tool_calls=[tool_call])
        assert resp.has_tool_calls is True

    def test_has_tool_calls_false(self):
        """has_tool_calls should return False when no tool calls."""
        resp = LLMResponse(content="Hello")
        assert resp.has_tool_calls is False


class TestLLMProviderABC:
    """Tests for LLMProvider abstract base class."""

    def test_cannot_instantiate(self):
        """LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()

    def test_subclass_implementation(self):
        """Subclass should implement abstract methods."""

        class MockProvider(LLMProvider):
            async def chat(
                self,
                messages,
                tools=None,
                model=None,
                max_tokens=4096,
                temperature=0.7,
            ) -> LLMResponse:
                return LLMResponse(content="Mock response")

            def get_default_model(self) -> str:
                return "mock-model"

        provider = MockProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.api_base is None
        assert provider.get_default_model() == "mock-model"

    def test_subclass_with_api_base(self):
        """Subclass should accept api_base."""

        class MockProvider(LLMProvider):
            async def chat(self, messages, **kwargs) -> LLMResponse:
                return LLMResponse(content="Mock")

            def get_default_model(self) -> str:
                return "mock"

        provider = MockProvider(
            api_key="key",
            api_base="https://api.example.com",
        )
        assert provider.api_base == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_subclass_chat(self):
        """Subclass chat method should work."""

        class MockProvider(LLMProvider):
            async def chat(
                self,
                messages,
                tools=None,
                model=None,
                max_tokens=4096,
                temperature=0.7,
            ) -> LLMResponse:
                return LLMResponse(
                    content=f"Received {len(messages)} messages",
                    usage={"prompt_tokens": 10, "completion_tokens": 5},
                )

            def get_default_model(self) -> str:
                return "mock"

        provider = MockProvider()
        response = await provider.chat([{"role": "user", "content": "Hi"}])
        assert response.content == "Received 1 messages"
        assert response.usage["prompt_tokens"] == 10
