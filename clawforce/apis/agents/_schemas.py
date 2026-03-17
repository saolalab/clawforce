"""Pydantic request/response schemas for agent endpoints."""

from pydantic import BaseModel, ConfigDict

from clawlib.config.schema import ChannelsConfig


class AgentCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str = ""
    template: str | None = None
    mode: str | None = None
    color: str = ""


class AgentUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    description: str | None = None
    color: str | None = None
    mode: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    max_tool_iterations: int | None = None
    memory_window: int | None = None
    fault_tolerance: dict | None = None
    enabled: bool | None = None
    onboarding_completed: bool | None = None
    tools: dict | None = None
    skills: dict | None = None
    channels: ChannelsConfig | None = None
    providers: dict | None = None
    heartbeat: dict | None = None
    security: dict | None = None


class A2AMessageBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
