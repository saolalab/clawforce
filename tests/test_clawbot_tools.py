"""Tests for clawbot.agent.tools module."""

from typing import Any

import pytest

from clawbot.agent.tools.base import Tool


class MockTool(Tool):
    """Mock tool implementation for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Input text"},
                "count": {"type": "integer", "minimum": 0, "maximum": 100},
                "enabled": {"type": "boolean"},
                "options": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string", "enum": ["fast", "slow"]},
                    },
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["text"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return f"Executed with: {kwargs}"


class TestToolABC:
    """Tests for Tool abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Tool cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Tool()

    def test_mock_tool_properties(self):
        """Mock tool should have correct properties."""
        tool = MockTool()
        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"
        assert "text" in tool.parameters["properties"]

    @pytest.mark.asyncio
    async def test_execute(self):
        """Tool execute should work."""
        tool = MockTool()
        result = await tool.execute(text="hello", count=5)
        assert "hello" in result
        assert "5" in result


class TestToolValidation:
    """Tests for Tool.validate_params method."""

    def test_valid_params(self):
        """Valid params should return empty error list."""
        tool = MockTool()
        errors = tool.validate_params({"text": "hello"})
        assert errors == []

    def test_missing_required(self):
        """Missing required param should return error."""
        tool = MockTool()
        errors = tool.validate_params({})
        assert len(errors) == 1
        assert "missing required" in errors[0]
        assert "text" in errors[0]

    def test_wrong_type_string(self):
        """Wrong type for string should return error."""
        tool = MockTool()
        errors = tool.validate_params({"text": 123})
        assert len(errors) == 1
        assert "should be string" in errors[0]

    def test_wrong_type_integer(self):
        """Wrong type for integer should return error."""
        tool = MockTool()
        errors = tool.validate_params({"text": "hi", "count": "not a number"})
        assert any("should be integer" in e for e in errors)

    def test_wrong_type_boolean(self):
        """Wrong type for boolean should return error."""
        tool = MockTool()
        errors = tool.validate_params({"text": "hi", "enabled": "yes"})
        assert any("should be boolean" in e for e in errors)

    def test_wrong_type_array(self):
        """Wrong type for array should return error."""
        tool = MockTool()
        errors = tool.validate_params({"text": "hi", "tags": "not-array"})
        assert any("should be array" in e for e in errors)

    def test_wrong_type_object(self):
        """Wrong type for object should return error."""
        tool = MockTool()
        errors = tool.validate_params({"text": "hi", "options": "not-object"})
        assert any("should be object" in e for e in errors)

    def test_minimum_constraint(self):
        """Value below minimum should return error."""
        tool = MockTool()
        errors = tool.validate_params({"text": "hi", "count": -1})
        assert any(">=" in e for e in errors)

    def test_maximum_constraint(self):
        """Value above maximum should return error."""
        tool = MockTool()
        errors = tool.validate_params({"text": "hi", "count": 101})
        assert any("<=" in e for e in errors)

    def test_enum_constraint(self):
        """Value not in enum should return error."""
        tool = MockTool()
        errors = tool.validate_params(
            {
                "text": "hi",
                "options": {"mode": "invalid"},
            }
        )
        assert any("must be one of" in e for e in errors)

    def test_nested_object_validation(self):
        """Nested object should be validated."""
        tool = MockTool()
        errors = tool.validate_params(
            {
                "text": "hi",
                "options": {"mode": "fast"},
            }
        )
        assert errors == []

    def test_array_items_validation(self):
        """Array items should be validated."""
        tool = MockTool()
        errors = tool.validate_params(
            {
                "text": "hi",
                "tags": ["tag1", 123, "tag3"],
            }
        )
        assert any("should be string" in e for e in errors)


class TestToolSchema:
    """Tests for Tool.to_schema method."""

    def test_to_schema_format(self):
        """to_schema should return OpenAI function format."""
        tool = MockTool()
        schema = tool.to_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "mock_tool"
        assert schema["function"]["description"] == "A mock tool for testing"
        assert "parameters" in schema["function"]

    def test_schema_parameters(self):
        """Schema parameters should match tool parameters."""
        tool = MockTool()
        schema = tool.to_schema()
        params = schema["function"]["parameters"]

        assert params["type"] == "object"
        assert "text" in params["properties"]
        assert "count" in params["properties"]
        assert params["required"] == ["text"]


class TestStringValidation:
    """Tests for string-specific validation."""

    def test_min_length(self):
        """String below minLength should return error."""

        class MinLengthTool(Tool):
            @property
            def name(self) -> str:
                return "min_length"

            @property
            def description(self) -> str:
                return "Test"

            @property
            def parameters(self) -> dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "minLength": 5},
                    },
                    "required": ["text"],
                }

            async def execute(self, **kwargs: Any) -> str:
                return "ok"

        tool = MinLengthTool()
        errors = tool.validate_params({"text": "hi"})
        assert any("at least" in e for e in errors)

    def test_max_length(self):
        """String above maxLength should return error."""

        class MaxLengthTool(Tool):
            @property
            def name(self) -> str:
                return "max_length"

            @property
            def description(self) -> str:
                return "Test"

            @property
            def parameters(self) -> dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "maxLength": 5},
                    },
                    "required": ["text"],
                }

            async def execute(self, **kwargs: Any) -> str:
                return "ok"

        tool = MaxLengthTool()
        errors = tool.validate_params({"text": "too long string"})
        assert any("at most" in e for e in errors)
