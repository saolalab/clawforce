"""Agent loop: the core processing engine."""

import asyncio
from typing import Awaitable, Callable

from loguru import logger

from clawbot.agent.agent_fs import AgentFS
from clawbot.agent.approval import ToolApprovalManager
from clawbot.agent.consolidator import MemoryConsolidator
from clawbot.agent.context import ContextBuilder
from clawbot.agent.loop.mcp import McpManager
from clawbot.agent.loop.session import SessionProcessor
from clawbot.agent.loop.tools import ToolsManager
from clawbot.agent.subagent import SubagentManager
from clawbot.agent.tools.mcp import MCPServerStatus
from clawbot.agent.tools.registry import ToolRegistry
from clawbot.core.cron import CronService
from clawbot.core.session import SessionManager
from clawbot.core.software import SoftwareManagement
from clawbot.providers.base import LLMProvider
from clawbot.providers.litellm_provider import LiteLLMProvider
from clawbot.providers.registry import find_by_model
from clawlib.bus import MessageBus, OutboundMessage
from clawlib.config.schema import (
    AgentDefaults,
    ControlPlaneConfig,
    ProviderConfig,
    SkillsConfig,
    ToolApprovalConfig,
    ToolsConfig,
)


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back

    Behaviour is composed from:
    - McpManager:       MCP server connection and lifecycle
    - ToolsManager:     tool registration, execution, and approval
    - SessionProcessor: message processing and the LLM iteration loop
    """

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        file_service: AgentFS,
        agent_defaults: AgentDefaults | None = None,
        tools_config: ToolsConfig | None = None,
        control_plane: ControlPlaneConfig | None = None,
        skills_config: SkillsConfig | None = None,
        cron_service: CronService | None = None,
        session_manager: SessionManager | None = None,
        software_management: SoftwareManagement | None = None,
        on_event: Callable[..., Awaitable[None]] | None = None,
    ):
        self._file_service = file_service
        self.workspace = file_service.workspace_path
        self.bus = bus
        self.provider = provider

        defaults = agent_defaults or AgentDefaults()
        self.model = defaults.model or provider.get_default_model()
        self.max_iterations = defaults.max_tool_iterations
        self.temperature = defaults.temperature
        self.max_tokens = defaults.max_tokens
        self.memory_window = defaults.memory_window
        self.max_tool_output_chars = defaults.max_tool_output_chars

        tools = tools_config or ToolsConfig()
        self.web_search_config = tools.web.search
        self.exec_config = tools.exec
        self.cron_service = cron_service
        self.restrict_to_workspace = tools.restrict_to_workspace
        self.ssrf_protection = tools.ssrf_protection

        skills = skills_config or SkillsConfig()
        self.context = ContextBuilder(
            self.workspace,
            profile_path=self._file_service.profile_path,
            disabled_skills=skills.disabled,
        )
        self.sessions = session_manager or SessionManager(
            sessions_dir=self._file_service.sessions_path
        )
        self.tools = ToolRegistry()
        self.mcp = ToolRegistry()
        self.subagents = SubagentManager(
            provider=provider,
            file_service=self._file_service,
            bus=bus,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            web_search_config=self.web_search_config,
            exec_config=self.exec_config,
            restrict_to_workspace=self.restrict_to_workspace,
            software_management=software_management,
            on_event=on_event,
        )

        self._running = False
        self.software_management = software_management
        self._on_event = on_event

        cp = control_plane or ControlPlaneConfig()
        self._admin_api_url = cp.admin_url or ""
        self._agent_token = cp.agent_token or ""
        self._agent_id = cp.agent_id or ""
        self._approval = ToolApprovalManager(bus=bus, config=tools.approval)
        self._consolidator = MemoryConsolidator(
            workspace=self.workspace, provider=provider, model=self.model
        )

        self._mcp_manager = McpManager(
            mcp_registry=self.mcp,
            initial_servers=dict(tools.mcp_servers) if tools.mcp_servers else None,
        )

        self._tools_manager = ToolsManager(
            tools=self.tools,
            mcp=self.mcp,
            approval=self._approval,
            bus=bus,
            subagents=self.subagents,
            file_service=file_service,
            workspace=self.workspace,
            exec_config=self.exec_config,
            web_search_config=self.web_search_config,
            restrict_to_workspace=self.restrict_to_workspace,
            ssrf_protection=self.ssrf_protection,
            max_tool_output_chars=self.max_tool_output_chars,
            admin_api_url=self._admin_api_url,
            agent_token=self._agent_token,
            agent_id=self._agent_id,
            cron_service=cron_service,
            on_event=on_event,
        )
        self._tools_manager.register_default_tools()

        self._session_processor = SessionProcessor(
            tools_manager=self._tools_manager,
            mcp_manager=self._mcp_manager,
            provider=provider,
            context=self.context,
            sessions=self.sessions,
            consolidator=self._consolidator,
            bus=bus,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_iterations=self.max_iterations,
            memory_window=self.memory_window,
            on_event=on_event,
            software_management=software_management,
        )

    # ── Hot-reload ────────────────────────────────────────────────────────────

    def update_tool_approval(self, cfg: ToolApprovalConfig) -> None:
        """Hot-reload tool approval config (called when admin updates config)."""
        self._approval.update_config(cfg)

    def update_provider_secrets(self, providers: dict) -> None:
        """Hot-reload provider API credentials.

        Prefer using ConfigEngine.hot_reload_providers() so the
        engine owns the flow; this method is the implementation that applies
        the given providers dict to the running LiteLLM provider and subagents.

        Args:
            providers: Dict of provider configs, e.g. {"gemini": {"api_key": "..."}}
        """
        if not isinstance(self.provider, LiteLLMProvider):
            logger.debug("[provider_secrets] Provider is not LiteLLM, skipping update")
            return

        spec = find_by_model(self.model)
        if not spec:
            logger.debug("[provider_secrets] No provider spec found for model: {}", self.model)
            return

        raw = providers.get(spec.name)
        if not isinstance(raw, dict):
            logger.debug("[provider_secrets] No config for provider: {}", spec.name)
            return
        pc = ProviderConfig.model_validate(raw)
        if not pc.api_key:
            logger.debug("[provider_secrets] No api_key for provider: {}", spec.name)
            return
        logger.info("[provider_secrets] Updating API key for provider: {}", spec.name)
        self.provider.update_credentials(
            api_key=pc.api_key,
            api_base=pc.api_base,
            extra_headers=pc.extra_headers,
        )

    def register_software(self, key: str, entry: dict) -> None:
        """Register software in the catalog at runtime (hot reload). Subagents use it via software_exec."""
        if self.software_management:
            self.software_management.register(key, entry)
        else:
            logger.warning("No software_management: cannot register software")

    def unregister_software(self, key: str) -> None:
        """Unregister software from the catalog at runtime (hot reload)."""
        if self.software_management:
            self.software_management.unregister(key)
        else:
            logger.warning("No software_management: cannot unregister software")

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def mcp_status(self) -> dict[str, MCPServerStatus]:
        """Per-server MCP connection status (populated after first connect)."""
        return self._mcp_manager.status

    async def close_mcp(self) -> None:
        """Close MCP connections."""
        await self._mcp_manager.close()

    async def register_mcp_server(self, key: str, config: dict) -> MCPServerStatus:
        """Register a new MCP server at runtime (delegates to McpManager)."""
        return await self._mcp_manager.register_server(key, config)

    def unregister_mcp_server(self, key: str) -> None:
        """Unregister an MCP server at runtime (delegates to McpManager)."""
        self._mcp_manager.unregister_server(key)

    def try_resolve_approval(self, msg) -> bool:
        """If this message is a yes/no reply for a pending tool approval, resolve and return True."""
        return self._tools_manager.try_resolve_approval(msg)

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_progress=None,
    ) -> str:
        """Process a message directly (delegates to SessionProcessor)."""
        return await self._session_processor.process_direct(
            content,
            session_key=session_key,
            channel=channel,
            chat_id=chat_id,
            on_progress=on_progress,
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        self._mcp_manager.connect()
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
                if self.try_resolve_approval(msg):
                    continue
                try:
                    response = await self._session_processor.process_message(msg)
                    if response:
                        await self.bus.publish_outbound(response)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.bus.publish_outbound(
                        OutboundMessage(
                            channel=msg.channel,
                            chat_id=msg.chat_id,
                            content=f"Sorry, I encountered an error: {str(e)}",
                        )
                    )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Agent loop consume_inbound error: {}", e)
                if not self._running:
                    break
                continue

    def stop(self) -> None:
        """Stop the agent loop (idempotent)."""
        if not self._running:
            return
        self._running = False
        logger.info("Agent loop stopping")
