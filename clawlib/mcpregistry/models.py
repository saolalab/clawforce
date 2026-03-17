"""MCP Registry data models."""

from pydantic import BaseModel, ConfigDict, Field


class MCPServerInfo(BaseModel):
    """MCP server metadata from the official registry."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: str = ""
    repository: str = ""
    homepage: str = ""
    version: str = ""
    license: str = ""
    author: str = ""
    is_verified: bool = False
    downloads: int = 0
    created_at: str = ""
    updated_at: str = ""
    categories: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    install_config: dict | list = Field(default_factory=dict)
