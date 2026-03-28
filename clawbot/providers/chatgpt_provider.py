"""ChatGPT Plus Provider — OAuth-based, same login as OpenAI Codex."""

from __future__ import annotations

import asyncio

from loguru import logger

from clawbot.providers.base import LLMResponse
from clawbot.providers.openai_codex_provider import (
    OpenAICodexProvider,
    _build_headers,
    _convert_messages,
    _convert_tools,
    _get_agent_oauth_token,
    _request_codex,
)

DEFAULT_CHATGPT_URL = "https://chatgpt.com/backend-api/codex/responses"
DEFAULT_MODEL = "chatgpt/gpt-4o"


class ChatGPTProvider(OpenAICodexProvider):
    """ChatGPT Plus provider.

    Uses the same OpenAI OAuth login as OpenAI Codex (shared ``codex.json``
    token file).  Strips the ``chatgpt/`` model prefix before sending the
    request so the bare model name (e.g. ``gpt-4o``) reaches the API.
    """

    def __init__(self, default_model: str = DEFAULT_MODEL):
        super().__init__(default_model=default_model)

    async def chat(
        self,
        messages: list,
        tools: list | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        model = model or self.default_model
        system_prompt, input_items = _convert_messages(messages)

        token = await asyncio.to_thread(_get_agent_oauth_token, "CHATGPT_OAUTH_TOKEN")
        headers = _build_headers(token.account_id, token.access)

        body = {
            "model": _strip_chatgpt_prefix(model),
            "store": False,
            "stream": True,
            "instructions": system_prompt,
            "input": input_items,
            "text": {"verbosity": "medium"},
            "include": ["reasoning.encrypted_content"],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
        }

        if tools:
            body["tools"] = _convert_tools(tools)

        try:
            try:
                content, tool_calls, finish_reason = await _request_codex(
                    DEFAULT_CHATGPT_URL, headers, body, verify=True
                )
            except Exception as e:
                if "CERTIFICATE_VERIFY_FAILED" not in str(e):
                    raise
                logger.warning(
                    "SSL certificate verification failed for ChatGPT API; retrying with verify=False"
                )
                content, tool_calls, finish_reason = await _request_codex(
                    DEFAULT_CHATGPT_URL, headers, body, verify=False
                )
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error calling ChatGPT: {str(e)}",
                finish_reason="error",
            )

    def get_default_model(self) -> str:
        return self.default_model


def _strip_chatgpt_prefix(model: str) -> str:
    if model.startswith("chatgpt/"):
        return model.split("/", 1)[1]
    return model
