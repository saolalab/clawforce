"""Agent runtime helpers: config loading and provider creation."""

from pathlib import Path
from typing import Any

from clawbot.core.config.loader import load_config
from clawbot.core.config.schema import Config
from clawbot.providers.chatgpt_provider import ChatGPTProvider
from clawbot.providers.custom_provider import CustomProvider
from clawbot.providers.litellm_provider import LiteLLMProvider
from clawbot.providers.openai_codex_provider import OpenAICodexProvider
from clawbot.providers.registry import find_by_name


def load_agent_config(config_path: Path) -> Config:
    """Load the complete agent config from an explicit path.

    Callers are responsible for resolving the config path, which should
    live **outside** the workspace directory to prevent agent tools from
    accessing secrets.
    """
    return load_config(config_path)


def make_provider(config: Config) -> Any:
    model = config.agents.defaults.model
    provider_name = config.get_provider_name(model)
    p = config.get_provider(model)

    if provider_name == "openai_codex" or (model or "").startswith("openai-codex/"):
        return OpenAICodexProvider(default_model=model)

    if provider_name == "chatgpt" or (model or "").startswith("chatgpt/"):
        return ChatGPTProvider(default_model=model)

    if provider_name == "custom":
        return CustomProvider(
            api_key=p.api_key if p else "no-key",
            api_base=config.get_api_base(model) or "http://localhost:8000/v1",
            default_model=model,
        )

    if provider_name:
        find_by_name(provider_name)
    return LiteLLMProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(model),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        provider_name=provider_name,
        fault_tolerance=config.agents.defaults.fault_tolerance,
    )
