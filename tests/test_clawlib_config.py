"""Tests for clawlib.config module."""

from clawlib.config.schema import (
    AgentDefaults,
    AgentsConfig,
    ChannelsConfig,
    Config,
    ControlPlaneConfig,
    DiscordConfig,
    DockerSecurityConfig,
    EmailConfig,
    ExecToolConfig,
    FaultToleranceConfig,
    FeishuConfig,
    GatewayConfig,
    HeartbeatConfig,
    MCPServerConfig,
    ProviderConfig,
    ProvidersConfig,
    SecurityConfig,
    ShellPolicyConfig,
    SkillsConfig,
    SlackConfig,
    SlackDMConfig,
    SoftwareEntry,
    TeamsConfig,
    TelegramConfig,
    ToolApprovalConfig,
    ToolsConfig,
    WebSearchConfig,
    WebToolsConfig,
    WhatsAppConfig,
    ZaloConfig,
    ZaloUserConfig,
)


class TestChannelConfigs:
    """Tests for individual channel configuration models."""

    def test_whatsapp_config_defaults(self):
        """WhatsApp config should have sensible defaults."""
        cfg = WhatsAppConfig()
        assert cfg.enabled is False
        assert cfg.allow_from == []

    def test_whatsapp_config_custom_values(self):
        """WhatsApp config should accept custom values."""
        cfg = WhatsAppConfig(
            enabled=True,
            allow_from=["user1", "user2"],
        )
        assert cfg.enabled is True
        assert cfg.allow_from == ["user1", "user2"]

    def test_telegram_config_defaults(self):
        """Telegram config should have sensible defaults."""
        cfg = TelegramConfig()
        assert cfg.enabled is False
        assert cfg.token == ""
        assert cfg.group_policy == "mention"
        assert cfg.proxy is None

    def test_telegram_config_with_proxy(self):
        """Telegram config should accept proxy setting."""
        cfg = TelegramConfig(
            enabled=True,
            token="bot:token",
            proxy="socks5://127.0.0.1:1080",
        )
        assert cfg.proxy == "socks5://127.0.0.1:1080"

    def test_discord_config_defaults(self):
        """Discord config should have correct defaults."""
        cfg = DiscordConfig()
        assert cfg.enabled is False
        assert cfg.gateway_url == "wss://gateway.discord.gg/?v=10&encoding=json"
        assert cfg.intents == 37377

    def test_email_config_defaults(self):
        """Email config should have correct defaults."""
        cfg = EmailConfig()
        assert cfg.enabled is False
        assert cfg.imap_port == 993
        assert cfg.smtp_port == 587
        assert cfg.imap_use_ssl is True
        assert cfg.smtp_use_tls is True
        assert cfg.poll_interval_seconds == 30
        assert cfg.max_body_chars == 12000

    def test_slack_config_defaults(self):
        """Slack config should have correct defaults."""
        cfg = SlackConfig()
        assert cfg.enabled is False
        assert cfg.mode == "socket"
        assert cfg.reply_in_thread is True
        assert cfg.react_emoji == "eyes"
        assert isinstance(cfg.dm, SlackDMConfig)
        assert cfg.dm.enabled is True

    def test_feishu_config_defaults(self):
        """Feishu config should have correct defaults."""
        cfg = FeishuConfig()
        assert cfg.enabled is False
        assert cfg.app_id == ""
        assert cfg.verification_token == ""

    def test_zalo_config_defaults(self):
        """Zalo OA config should have correct defaults."""
        cfg = ZaloConfig()
        assert cfg.enabled is False
        assert cfg.bot_token == ""
        assert cfg.allow_from == []
        assert cfg.group_policy == "allowlist"
        assert cfg.group_allow_from == []
        assert cfg.media_max_mb == 5

    def test_zalouser_config_defaults(self):
        """Zalo Personal config should have correct defaults."""
        cfg = ZaloUserConfig()
        assert cfg.enabled is False
        assert cfg.allow_from == []
        assert cfg.group_policy == "mention"

    def test_teams_config_defaults(self):
        """Teams config should have correct defaults."""
        cfg = TeamsConfig()
        assert cfg.enabled is False
        assert cfg.app_id == ""
        assert cfg.app_password == ""
        assert cfg.allow_from == []


class TestAgentConfig:
    """Tests for agent configuration."""

    def test_agent_defaults(self):
        """AgentDefaults should have correct defaults."""
        defaults = AgentDefaults()
        assert defaults.model == "anthropic/claude-opus-4-5"
        assert defaults.max_tokens == 8192
        assert defaults.temperature == 0.7
        assert defaults.max_tool_iterations == 20
        assert defaults.memory_window == 50
        assert defaults.max_tool_output_chars == 16000
        assert isinstance(defaults.fault_tolerance, FaultToleranceConfig)

    def test_fault_tolerance_config(self):
        """FaultToleranceConfig should have correct defaults."""
        cfg = FaultToleranceConfig()
        assert cfg.max_attempts == 3
        assert cfg.backoff_factor == 1.0

    def test_agents_config(self):
        """AgentsConfig should contain defaults."""
        cfg = AgentsConfig()
        assert isinstance(cfg.defaults, AgentDefaults)


class TestProvidersConfig:
    """Tests for provider configuration."""

    def test_provider_config_defaults(self):
        """ProviderConfig should have correct defaults."""
        cfg = ProviderConfig()
        assert cfg.api_key == ""
        assert cfg.api_base is None
        assert cfg.extra_headers is None

    def test_provider_config_custom(self):
        """ProviderConfig should accept custom values."""
        cfg = ProviderConfig(
            api_key="sk-xxx",
            api_base="https://api.example.com",
            extra_headers={"X-Custom": "value"},
        )
        assert cfg.api_key == "sk-xxx"
        assert cfg.api_base == "https://api.example.com"
        assert cfg.extra_headers == {"X-Custom": "value"}

    def test_providers_config_all_providers(self):
        """ProvidersConfig should contain all provider types."""
        cfg = ProvidersConfig()
        assert isinstance(cfg.custom, ProviderConfig)
        assert isinstance(cfg.anthropic, ProviderConfig)
        assert isinstance(cfg.openai, ProviderConfig)
        assert isinstance(cfg.openrouter, ProviderConfig)
        assert isinstance(cfg.deepseek, ProviderConfig)
        assert isinstance(cfg.groq, ProviderConfig)
        assert isinstance(cfg.gemini, ProviderConfig)
        assert isinstance(cfg.zhipu, ProviderConfig)
        assert isinstance(cfg.dashscope, ProviderConfig)
        assert isinstance(cfg.moonshot, ProviderConfig)
        assert isinstance(cfg.minimax, ProviderConfig)
        assert isinstance(cfg.aihubmix, ProviderConfig)
        assert isinstance(cfg.siliconflow, ProviderConfig)
        assert isinstance(cfg.openai_codex, ProviderConfig)
        assert isinstance(cfg.github_copilot, ProviderConfig)


class TestToolsConfig:
    """Tests for tools configuration."""

    def test_shell_policy_defaults(self):
        """ShellPolicyConfig should have correct defaults."""
        cfg = ShellPolicyConfig()
        assert cfg.mode == "allow_all"
        assert cfg.allow == []
        assert cfg.deny == []
        assert cfg.relaxed is False

    def test_exec_tool_config(self):
        """ExecToolConfig should have correct defaults."""
        cfg = ExecToolConfig()
        assert cfg.timeout == 60
        assert isinstance(cfg.policy, ShellPolicyConfig)

    def test_mcp_server_config(self):
        """MCPServerConfig should have correct defaults."""
        cfg = MCPServerConfig()
        assert cfg.command == ""
        assert cfg.args == []
        assert cfg.env == {}
        assert cfg.url == ""
        assert cfg.headers == {}

    def test_mcp_server_config_custom(self):
        """MCPServerConfig should accept custom values."""
        cfg = MCPServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-fs"],
            env={"DEBUG": "1"},
        )
        assert cfg.command == "npx"
        assert cfg.args == ["-y", "@modelcontextprotocol/server-fs"]
        assert cfg.env == {"DEBUG": "1"}

    def test_tools_config_structure(self):
        """ToolsConfig should have all components."""
        cfg = ToolsConfig()
        assert isinstance(cfg.web, WebToolsConfig)
        assert isinstance(cfg.exec, ExecToolConfig)
        assert cfg.restrict_to_workspace is True
        assert cfg.ssrf_protection is True
        assert cfg.mcp_servers == {}
        assert cfg.software == {}
        assert isinstance(cfg.approval, ToolApprovalConfig)


class TestWebConfig:
    """Tests for web search configuration."""

    def test_web_search_defaults(self):
        """WebSearchConfig should have correct defaults."""
        cfg = WebSearchConfig()
        assert cfg.provider == "duckduckgo"
        assert cfg.max_results == 5
        assert cfg.brave_api_key == ""
        assert cfg.serpapi_api_key == ""


class TestGatewayConfig:
    """Tests for gateway configuration."""

    def test_gateway_defaults(self):
        """GatewayConfig should have correct defaults."""
        cfg = GatewayConfig()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 18790


class TestHeartbeatConfig:
    """Tests for heartbeat configuration."""

    def test_heartbeat_defaults(self):
        """HeartbeatConfig should have correct defaults."""
        cfg = HeartbeatConfig()
        assert cfg.enabled is True
        assert cfg.interval_s == 30 * 60
        assert cfg.cron_expr == ""
        assert cfg.timezone == ""


class TestRootConfig:
    """Tests for root Config model."""

    def test_config_defaults(self):
        """Config should create with all subsections."""
        cfg = Config()
        assert isinstance(cfg.agents, AgentsConfig)
        assert isinstance(cfg.channels, ChannelsConfig)
        assert isinstance(cfg.providers, ProvidersConfig)
        assert isinstance(cfg.gateway, GatewayConfig)
        assert isinstance(cfg.tools, ToolsConfig)
        assert isinstance(cfg.skills, SkillsConfig)
        assert isinstance(cfg.heartbeat, HeartbeatConfig)
        assert isinstance(cfg.control_plane, ControlPlaneConfig)
        assert isinstance(cfg.security, SecurityConfig)

    def test_channels_config_all_channels(self):
        """ChannelsConfig should contain all channel types."""
        cfg = ChannelsConfig()
        assert isinstance(cfg.whatsapp, WhatsAppConfig)
        assert isinstance(cfg.telegram, TelegramConfig)
        assert isinstance(cfg.discord, DiscordConfig)
        assert isinstance(cfg.feishu, FeishuConfig)
        assert isinstance(cfg.email, EmailConfig)
        assert isinstance(cfg.slack, SlackConfig)
        assert isinstance(cfg.zalo, ZaloConfig)
        assert isinstance(cfg.zalouser, ZaloUserConfig)
        assert isinstance(cfg.teams, TeamsConfig)


class TestCamelCaseSupport:
    """Tests for camelCase/snake_case alias support."""

    def test_telegram_config_snake_case(self):
        """Telegram config should accept snake_case keys."""
        cfg = TelegramConfig.model_validate(
            {
                "enabled": True,
                "group_policy": "all",
                "allow_from": ["user1"],
            }
        )
        assert cfg.enabled is True
        assert cfg.group_policy == "all"
        assert cfg.allow_from == ["user1"]

    def test_email_config_snake_case(self):
        """Email config should accept snake_case keys."""
        cfg = EmailConfig.model_validate(
            {
                "enabled": True,
                "imap_host": "imap.gmail.com",
                "smtp_host": "smtp.gmail.com",
                "poll_interval_seconds": 60,
            }
        )
        assert cfg.imap_host == "imap.gmail.com"
        assert cfg.smtp_host == "smtp.gmail.com"
        assert cfg.poll_interval_seconds == 60


class TestSoftwareEntry:
    """Tests for SoftwareEntry model."""

    def test_defaults(self):
        """SoftwareEntry should have correct defaults."""
        entry = SoftwareEntry()
        assert entry.name == ""
        assert entry.description == ""
        assert entry.command == ""
        assert entry.args == []
        assert entry.env == {}
        assert entry.installed_via == ""
        assert entry.package == ""
        assert entry.stdin is False

    def test_custom_values(self):
        """SoftwareEntry should accept custom values."""
        entry = SoftwareEntry(
            name="eslint",
            description="JavaScript linter",
            command="npx",
            args=["eslint", "--fix"],
            env={"NODE_ENV": "production"},
            installed_via="npm",
            package="eslint",
            stdin=True,
        )
        assert entry.name == "eslint"
        assert entry.description == "JavaScript linter"
        assert entry.command == "npx"
        assert entry.args == ["eslint", "--fix"]
        assert entry.env == {"NODE_ENV": "production"}
        assert entry.installed_via == "npm"
        assert entry.package == "eslint"
        assert entry.stdin is True


class TestToolApprovalConfig:
    """Tests for ToolApprovalConfig model."""

    def test_defaults(self):
        """ToolApprovalConfig should have correct defaults."""
        cfg = ToolApprovalConfig()
        assert cfg.default_mode == "always_run"
        assert cfg.per_tool == {}
        assert cfg.timeout_seconds == 120

    def test_custom_values(self):
        """ToolApprovalConfig should accept custom values."""
        cfg = ToolApprovalConfig(
            default_mode="ask_before_run",
            per_tool={"exec": "ask_before_run", "read_file": "always_run"},
            timeout_seconds=60,
        )
        assert cfg.default_mode == "ask_before_run"
        assert cfg.per_tool["exec"] == "ask_before_run"
        assert cfg.timeout_seconds == 60


class TestControlPlaneConfig:
    """Tests for ControlPlaneConfig model."""

    def test_defaults(self):
        """ControlPlaneConfig should have correct defaults."""
        cfg = ControlPlaneConfig()
        assert cfg.admin_url == ""
        assert cfg.agent_id == ""
        assert cfg.agent_token == ""
        assert cfg.heartbeat_interval == 30

    def test_custom_values(self):
        """ControlPlaneConfig should accept custom values."""
        cfg = ControlPlaneConfig(
            admin_url="https://admin.example.com",
            agent_id="agent-1",
            agent_token="token-secret",
            heartbeat_interval=60,
        )
        assert cfg.admin_url == "https://admin.example.com"
        assert cfg.agent_id == "agent-1"
        assert cfg.agent_token == "token-secret"
        assert cfg.heartbeat_interval == 60


class TestDockerSecurityConfig:
    """Tests for DockerSecurityConfig model."""

    def test_defaults(self):
        """DockerSecurityConfig should have correct defaults."""
        cfg = DockerSecurityConfig()
        assert cfg.level == "permissive"
        assert cfg.read_only is None
        assert cfg.network_mode is None
        assert cfg.pids_limit is None
        assert cfg.mem_limit is None
        assert cfg.cpu_quota is None
        assert cfg.cpu_period is None

    def test_custom_values(self):
        """DockerSecurityConfig should accept custom values."""
        cfg = DockerSecurityConfig(
            level="sandboxed",
            read_only=True,
            network_mode="none",
            pids_limit=100,
            mem_limit="512m",
            cpu_quota=50000,
            cpu_period=100000,
        )
        assert cfg.level == "sandboxed"
        assert cfg.read_only is True
        assert cfg.network_mode == "none"
        assert cfg.pids_limit == 100
        assert cfg.mem_limit == "512m"
        assert cfg.cpu_quota == 50000
        assert cfg.cpu_period == 100000


class TestSecurityConfig:
    """Tests for SecurityConfig model."""

    def test_defaults(self):
        """SecurityConfig should have correct defaults."""
        cfg = SecurityConfig()
        assert isinstance(cfg.docker, DockerSecurityConfig)
        assert cfg.docker.level == "permissive"
