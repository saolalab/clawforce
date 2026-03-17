"""Config engine: single load (local + admin merge), schema-based deserialization.

- Config domain: full Config (plain + secrets). Plain persisted to agent.json; secrets
  never written to disk. Env vars come from AgentVariablesStore via pool at spawn.
- One load path: load(admin_blob=None) = local file merged with optional admin overlay.
"""

import asyncio
import os
from pathlib import Path
from typing import Any

from loguru import logger

from clawbot.core.config.loader import load_config, save_config
from clawbot.core.config.schema import Config
from clawbot.providers.registry import PROVIDERS
from clawlib.config.helpers import SECRET_SECTIONS
from clawlib.config.loader import deep_merge
from clawlib.config.schema import ToolsConfig

# Channel config key -> env var name (schema-driven via ChannelsConfig fields)
_CHANNEL_ENV_MAP = {
    "telegram": [("token", "TELEGRAM_BOT_TOKEN")],
    "discord": [("token", "DISCORD_BOT_TOKEN")],
    "slack": [("bot_token", "SLACK_BOT_TOKEN"), ("app_token", "SLACK_APP_TOKEN")],
    "feishu": [("app_id", "FEISHU_APP_ID"), ("app_secret", "FEISHU_APP_SECRET")],
}


class ConfigEngine:
    """Single config store. load() = local + admin merge. Schema deserializes everything."""

    def __init__(self, config_path: Path, agent_loop: Any = None) -> None:
        self._config_path = config_path
        self._agent_loop = agent_loop
        self._config: Config | None = None

    # -- Loading --------------------------------------------------------------

    def load(self, admin_blob: dict | None = None) -> None:
        """Load config: local file merged with optional admin overlay.

        Always loads from agent.json first. If admin_blob is provided (online),
        deep-merges it on top. Deserializes via Config.model_validate.
        Plain config saved to file; secrets never persisted.
        """
        local = load_config(self._config_path)
        merged = deep_merge(
            local.model_dump(by_alias=False),
            admin_blob or {},
            replace_empty=True,
        )
        self._config = Config.model_validate(merged)

        plain = {k: v for k, v in merged.items() if k not in SECRET_SECTIONS}
        save_config(plain, self._config_path)

    def merge(self, blob: dict) -> None:
        """Merge blob into current config (hot-reload). Schema validates."""
        if not blob:
            return
        current = self._config.model_dump(by_alias=False) if self._config else {}
        merged = deep_merge(current, blob, replace_empty=True)
        self._config = Config.model_validate(merged)

    # -- Properties -----------------------------------------------------------

    @property
    def config(self) -> Config:
        if self._config is None:
            raise RuntimeError("Config not loaded. Call load() first.")
        return self._config

    @property
    def full_config(self) -> Config:
        """Alias for config; kept for API compatibility with runtime and handlers."""
        return self.config

    def config_dict(self) -> dict:
        """Plain config only (for get_config WS response)."""
        if self._config is None:
            return {}
        d = self._config.model_dump(by_alias=False)
        return {k: v for k, v in d.items() if k not in SECRET_SECTIONS}

    def secrets_dict(self) -> dict:
        """Secrets only (for put_secrets and internal use)."""
        if self._config is None:
            return {}
        d = self._config.model_dump(by_alias=False)
        return {k: d[k] for k in SECRET_SECTIONS if k in d}

    # -- Env injection --------------------------------------------------------

    def inject_to_env(self) -> None:
        """Inject providers and channels into os.environ."""
        cfg = self.config
        for spec in PROVIDERS:
            if not spec.env_key:
                continue
            provider = getattr(cfg.providers, spec.name, None)
            if provider is None:
                continue
            if provider.api_key and not provider.api_key.startswith("***"):
                os.environ.setdefault(spec.env_key, provider.api_key)
                for env_name, env_template in spec.env_extras:
                    resolved = env_template.replace("{api_key}", provider.api_key)
                    if provider.api_base:
                        resolved = resolved.replace("{api_base}", provider.api_base)
                    os.environ.setdefault(env_name, resolved)

        for channel_name, env_mappings in _CHANNEL_ENV_MAP.items():
            ch = getattr(cfg.channels, channel_name, None)
            if ch is None:
                continue
            for config_key, env_key in env_mappings:
                value = getattr(ch, config_key, None)
                if value and isinstance(value, str) and not value.startswith("***"):
                    os.environ.setdefault(env_key, value)

    # -- Hot-reload -----------------------------------------------------------

    async def apply_update(self, body: dict) -> dict:
        """Merge plain config, persist, hot-reload tools/MCP. Secrets in body ignored."""
        plain = {k: v for k, v in body.items() if k not in SECRET_SECTIONS}
        if not plain:
            return self.config_dict()

        # Normalize camelCase via schema before merge; secrets sections are already stripped
        plain = Config.model_validate(plain).model_dump(by_alias=False)

        old_tools = (self._config.model_dump(by_alias=False) if self._config else {}).get("tools")
        self.merge(plain)

        to_save = {
            k: v
            for k, v in self._config.model_dump(by_alias=False).items()
            if k not in SECRET_SECTIONS
        }
        save_config(to_save, self._config_path)

        tools_changed = old_tools != to_save.get("tools")
        if self._agent_loop and tools_changed:
            self._reload_tool_approval(self._config.tools)
            task = asyncio.ensure_future(self._reload_mcp_servers(self._config.tools))
            task.add_done_callback(
                lambda t: (
                    logger.exception("[config_engine] MCP reload failed: {}", t.exception())
                    if not t.cancelled() and t.exception()
                    else None
                )
            )
            # Reload software catalog so per-software env (e.g. GH_TOKEN) is picked up
            if getattr(self._agent_loop, "software_management", None):
                self._agent_loop.software_management.reload()
                logger.info("[config_engine] Software catalog reloaded (tools.software changed)")

        return self.config_dict()

    def hot_reload_providers(self) -> None:
        if self._agent_loop and hasattr(self._agent_loop, "update_provider_secrets"):
            providers_dict = self._config.providers.model_dump(exclude_none=True)
            self._agent_loop.update_provider_secrets(providers_dict)

    def _reload_tool_approval(self, tools: ToolsConfig) -> None:
        try:
            self._agent_loop.update_tool_approval(tools.approval)
            logger.info(
                "[config_engine] Tool approval updated: default_mode={}, per_tool={}",
                tools.approval.default_mode,
                tools.approval.per_tool,
            )
        except Exception as e:
            logger.exception("[config_engine] Failed to reload tool approval: {}", e)

    async def _reload_mcp_servers(self, tools: ToolsConfig) -> None:
        if self._agent_loop is None:
            return
        try:
            mcp_status = self._agent_loop.mcp_status  # {key: MCPServerStatus}
            current = set(mcp_status.keys()) if mcp_status else set()
            desired = set(tools.mcp_servers) if tools.mcp_servers else set()

            for key in current - desired:
                logger.info("[config_engine] Unregistering MCP server: {}", key)
                self._agent_loop.unregister_mcp_server(key)

            for key in desired - current:
                server_config = tools.mcp_servers[key].model_dump(exclude_none=True)
                logger.info("[config_engine] Registering MCP server: {}", key)
                status = await self._agent_loop.register_mcp_server(key, server_config)
                logger.info("[config_engine] MCP server {} status: {}", key, status.status)
        except Exception as e:
            logger.exception("[config_engine] Failed to reload MCP servers: {}", e)
