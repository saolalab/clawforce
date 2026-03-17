"""Tool registry for dynamic tool management. Supports entry-point discovery via clawbot.tools."""

from typing import Any

from clawbot.agent.tools.base import Tool


def discover_tools_from_entry_points() -> list[Tool]:
    """Load tools from [project.entry-points] clawbot.tools. Returns list of Tool instances."""
    tools: list[Tool] = []
    try:
        from importlib.metadata import entry_points

        eps = entry_points(group="clawbot.tools")
        for ep in eps:
            try:
                cls = ep.load()
                if issubclass(cls, Tool):
                    tools.append(cls())
            except Exception:
                pass
    except Exception:
        pass
    return tools


class ToolRegistry:
    """
    Registry for agent tools.

    Allows dynamic registration and execution of tools.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def register_plugins(self) -> None:
        """Register any tools from clawbot.tools entry points."""
        for tool in discover_tools_from_entry_points():
            self.register(tool)

    def unregister(self, name: str) -> None:
        """Unregister a tool by name."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def get_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions in OpenAI format."""
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """
        Execute a tool by name with given parameters.

        Args:
            name: Tool name.
            params: Tool parameters.

        Returns:
            Tool execution result as string.

        Raises:
            KeyError: If tool not found.
        """
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        try:
            errors = tool.validate_params(params)
            if errors:
                return f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors)
            return await tool.execute(**params)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

    @property
    def tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())

    def get_tools_summary(self) -> str:
        """Get a human-readable summary of all tools for system prompt.

        Returns a formatted string describing each tool's name and description.
        """
        if not self._tools:
            return ""
        lines = []
        for name, tool in self._tools.items():
            desc = (
                tool.description[:100] + "..." if len(tool.description) > 100 else tool.description
            )
            lines.append(f"- `{name}`: {desc}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
