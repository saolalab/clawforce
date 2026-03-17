"""Registry abstraction for Skill, MCP, and Software marketplaces."""

from clawlib.registry.factory import (
    get_mcp_registry,
    get_skill_registry,
    get_software_registry,
)
from clawlib.registry.protocols import MCPRegistry, SkillRegistry, SoftwareRegistry

__all__ = [
    "MCPRegistry",
    "SkillRegistry",
    "SoftwareRegistry",
    "get_mcp_registry",
    "get_skill_registry",
    "get_software_registry",
]
