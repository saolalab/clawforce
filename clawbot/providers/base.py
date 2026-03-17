"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

_IMAGE_UNSUPPORTED_MARKERS = (
    "image_url is only supported",
    "does not support image",
    "images are not supported",
    "image input is not supported",
    "image_url is not supported",
    "unsupported image input",
)


def _is_image_unsupported_error(content: str | None) -> bool:
    """Return True if the error message indicates the model does not support image input."""
    err = (content or "").lower()
    return any(marker in err for marker in _IMAGE_UNSUPPORTED_MARKERS)


def _strip_image_content(messages: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    """Replace image_url blocks with text placeholder. Returns None if no images found."""
    found = False
    result = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            new_content = []
            for b in content:
                if isinstance(b, dict) and b.get("type") == "image_url":
                    new_content.append({"type": "text", "text": "[image omitted]"})
                    found = True
                else:
                    new_content.append(b)
            result.append({**msg, "content": new_content})
        else:
            result.append(msg)
    return result if found else None


@dataclass
class ToolCallRequest:
    """A tool call request from the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    reasoning_content: str | None = None  # Kimi, DeepSeek-R1 etc.

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Implementations should handle the specifics of each provider's API
    while maintaining a consistent interface.
    """

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        self.api_key = api_key
        self.api_base = api_base

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions.
            model: Model identifier (provider-specific).
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with content and/or tool calls.
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        pass
