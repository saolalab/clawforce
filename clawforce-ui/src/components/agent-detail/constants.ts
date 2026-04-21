import React from "react";
import { SiTelegram, SiDiscord, SiWhatsapp, SiSlack } from "react-icons/si";
import { MdEmail } from "react-icons/md";
import { FeishuIcon, TeamsIcon } from "./ui/Icons";
import type { ActivityFilter, FieldDef, ProviderDef } from "./types";

export const css = {
  label: "block text-xs font-medium text-claude-text-muted mb-1",
  input:
    "w-full rounded-lg border border-claude-border bg-claude-bg px-3 py-1.5 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
  card: "rounded-xl border border-claude-border bg-claude-input p-4",
  cardTitle: "text-sm font-semibold text-claude-text-primary",
  btn: "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer",
  toggle:
    "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors",
};

export const HEARTBEAT_SCHEDULE_OPTIONS: { value: number; label: string }[] = [
  { value: 30 * 60, label: "30 minutes" },
  { value: 60 * 60, label: "1 hour" },
  { value: 2 * 60 * 60, label: "2 hours" },
  { value: 3 * 60 * 60, label: "3 hours" },
  { value: 6 * 60 * 60, label: "6 hours" },
  { value: 12 * 60 * 60, label: "12 hours" },
  { value: 24 * 60 * 60, label: "24 hours" },
];

export const CHANNEL_DEFS: { key: string; label: string; icon: React.ReactNode; fields: FieldDef[] }[] = [
  {
    key: "telegram",
    label: "Telegram",
    icon: React.createElement(SiTelegram, { size: 20, style: { color: "#26A5E4" } }),
    fields: [
      { name: "enabled", label: "Enable Telegram", type: "toggle" },
      { name: "token", label: "Bot Token", type: "password", placeholder: "From @BotFather" },
      { name: "allow_from", label: "Allowed Users", type: "tags", placeholder: "user_id1, user_id2" },
      { name: "proxy", label: "Proxy", type: "text", placeholder: "http://127.0.0.1:7890" },
    ],
  },
  {
    key: "discord",
    label: "Discord",
    icon: React.createElement(SiDiscord, { size: 20, style: { color: "#5865F2" } }),
    fields: [
      { name: "enabled", label: "Enable Discord", type: "toggle" },
      { name: "token", label: "Bot Token", type: "password", placeholder: "Token from Discord Developer Portal" },
      { name: "allow_from", label: "Allowed Users", type: "tags", placeholder: "user_id1, user_id2" },
    ],
  },
  {
    key: "whatsapp",
    label: "WhatsApp",
    icon: React.createElement(SiWhatsapp, { size: 20, style: { color: "#25D366" } }),
    fields: [
      { name: "enabled", label: "Enable WhatsApp", type: "toggle" },
      { name: "allow_from", label: "Allowed Numbers", type: "tags", placeholder: "+1234567890" },
    ],
  },
  {
    key: "slack",
    label: "Slack",
    icon: React.createElement(SiSlack, { size: 20, style: { color: "#4A154B" } }),
    fields: [
      { name: "enabled", label: "Enable Slack", type: "toggle" },
      { name: "bot_token", label: "Bot Token", type: "password", placeholder: "xoxb-..." },
      { name: "app_token", label: "App Token", type: "password", placeholder: "xapp-..." },
      { name: "reply_in_thread", label: "Reply in Thread", type: "toggle" },
    ],
  },
  // Zalo (OA + Personal) — disabled for now, enable later
  // {
  //   key: "zalo",
  //   label: "Zalo (Official Account)",
  //   icon: React.createElement(SiZalo, { size: 20, style: { color: "#0068FF" } }),
  //   fields: [
  //     { name: "enabled", label: "Enable Zalo OA", type: "toggle" },
  //     { name: "bot_token", label: "Bot Token", type: "password", placeholder: "From Zalo Bot Platform (12345689:abc-xyz)" },
  //     { name: "allow_from", label: "Allowed Users", type: "tags", placeholder: "user_id1, user_id2" },
  //   ],
  // },
  // {
  //   key: "zalouser",
  //   label: "Zalo Personal",
  //   icon: React.createElement(SiZalo, { size: 20, style: { color: "#0068FF" } }),
  //   fields: [
  //     { name: "enabled", label: "Enable Zalo Personal", type: "toggle" },
  //     { name: "allow_from", label: "Allowed Users", type: "tags", placeholder: "user_id1, user_id2" },
  //   ],
  // },
  {
    key: "teams",
    label: "Microsoft Teams",
    icon: React.createElement(TeamsIcon, { size: 20 }),
    fields: [
      { name: "enabled", label: "Enable Teams", type: "toggle" },
      { name: "app_id", label: "App ID", type: "text", placeholder: "From Azure Bot registration" },
      { name: "app_password", label: "App Password", type: "password", placeholder: "From Azure Bot registration" },
      { name: "allow_from", label: "Allowed Users", type: "tags", placeholder: "user_id1, user_id2" },
    ],
  },
  {
    key: "feishu",
    label: "Feishu / Lark",
    icon: React.createElement(FeishuIcon, { size: 20 }),
    fields: [
      { name: "enabled", label: "Enable Feishu", type: "toggle" },
      { name: "app_id", label: "App ID", type: "text", placeholder: "Feishu Open Platform App ID" },
      { name: "app_secret", label: "App Secret", type: "password", placeholder: "App Secret" },
    ],
  },
  {
    key: "email",
    label: "Email",
    icon: React.createElement(MdEmail, { size: 20 }),
    fields: [
      { name: "enabled", label: "Enable Email", type: "toggle" },
      { name: "imap_host", label: "IMAP Host", type: "text", placeholder: "imap.gmail.com" },
      { name: "imap_port", label: "IMAP Port", type: "number", placeholder: "993" },
      { name: "imap_username", label: "IMAP Username", type: "text" },
      { name: "imap_password", label: "IMAP Password", type: "password" },
      { name: "smtp_host", label: "SMTP Host", type: "text", placeholder: "smtp.gmail.com" },
      { name: "smtp_port", label: "SMTP Port", type: "number", placeholder: "587" },
      { name: "smtp_username", label: "SMTP Username", type: "text" },
      { name: "smtp_password", label: "SMTP Password", type: "password" },
      { name: "from_address", label: "From Address", type: "text", placeholder: "bot@example.com" },
    ],
  },
];

export const PROVIDER_DEFS: ProviderDef[] = [
  // Subscription-based (OAuth) — no API key required
  { field: "chatgpt", label: "ChatGPT Plus", keywords: ["chatgpt"], oauth: true },
  { field: "openai_codex", label: "OpenAI Codex", keywords: ["openai-codex", "codex"], oauth: true },
  // API key / token providers
  { field: "custom", label: "Custom (OpenAI-compatible)", keywords: ["custom/"] },
  { field: "anthropic", label: "Anthropic", keywords: ["anthropic", "claude"] },
  { field: "openai", label: "OpenAI", keywords: ["openai", "gpt", "o1", "o3", "o4"] },
  { field: "openrouter", label: "OpenRouter", keywords: ["openrouter"] },
  { field: "deepseek", label: "DeepSeek", keywords: ["deepseek"] },
  { field: "gemini", label: "Google Gemini", keywords: ["gemini"] },
  { field: "groq", label: "Groq", keywords: ["groq"] },
  { field: "mistral", label: "Mistral AI", keywords: ["mistral"] },
  { field: "xai", label: "xAI (Grok)", keywords: ["xai", "grok"] },
  { field: "together", label: "Together AI", keywords: ["together"] },
  { field: "bedrock", label: "AWS Bedrock", keywords: ["bedrock"] },
  { field: "azure", label: "Azure OpenAI", keywords: ["azure"] },
  // GitHub Copilot — paste token from `gh auth token` or VS Code Copilot extension
  { field: "github_copilot", label: "GitHub Copilot", keywords: ["github_copilot", "copilot"] },
  { field: "moonshot", label: "Moonshot / Kimi", keywords: ["moonshot", "kimi"] },
  { field: "dashscope", label: "DashScope / Qwen", keywords: ["dashscope", "qwen"] },
  { field: "zhipu", label: "Zhipu AI", keywords: ["zhipu", "glm"] },
  { field: "minimax", label: "MiniMax", keywords: ["minimax"] },
  { field: "aihubmix", label: "AiHubMix", keywords: ["aihubmix"] },
  { field: "siliconflow", label: "SiliconFlow", keywords: ["siliconflow"] },
  { field: "vllm", label: "vLLM / Local", keywords: ["vllm"] },
];

export const SECURITY_PRESETS = {
  permissive: {
    name: "Standard",
    tagline: "Internet access, normal agent",
    description: "Best for agents that need to browse the web, call APIs, or install catalog software.",
    features: [
      { label: "Internet access", enabled: true },
      { label: "Can save files", enabled: true },
      { label: "Catalog software install", enabled: true },
      { label: "Memory", value: "2 GB" },
      { label: "CPU", value: "1 core" },
    ],
  },
  sandboxed: {
    name: "Safe",
    tagline: "No internet, maximum protection",
    description: "Best for running untrusted code or sensitive tasks. Agent works in complete isolation.",
    features: [
      { label: "Internet access", enabled: false },
      { label: "Can save files", enabled: false },
      { label: "Memory", value: "1 GB" },
      { label: "CPU", value: "1 core" },
    ],
  },
  privileged: {
    name: "Full Access",
    tagline: "Full system access, can install software",
    description:
      "Agent runs as root with full capabilities. Can install system packages (apt-get, sudo). Use only in trusted environments.",
    features: [
      { label: "Internet access", enabled: true },
      { label: "Can save files", enabled: true },
      { label: "sudo / apt-get", enabled: true },
      { label: "Memory", value: "2 GB" },
      { label: "CPU", value: "1 core" },
    ],
  },
};

export const PRESET_ROWS: [string, string][] = [
  ["mem_limit", "Memory limit"],
  ["cpu_quota", "CPU quota"],
  ["cpu_period", "CPU period"],
  ["security_opt", "Security options"],
  ["cap_drop", "Restricted capabilities"],
  ["cap_add", "Extra capabilities"],
  ["read_only", "Read-only system"],
  ["network_mode", "Network"],
  ["pids_limit", "Process limit"],
  ["tmpfs", "Temp storage"],
];

export const BUILTIN_TOOLS = [
  { value: "exec", label: "Shell (exec)" },
  { value: "read_file", label: "Read file" },
  { value: "write_file", label: "Write file" },
  { value: "edit_file", label: "Edit file" },
  { value: "list_dir", label: "List directory" },
  { value: "workspace_tree", label: "Workspace tree" },
  { value: "web_search", label: "Web search" },
  { value: "web_fetch", label: "Web fetch" },
  { value: "message", label: "Message" },
  { value: "spawn", label: "Spawn sub-agent" },
  { value: "a2a_call", label: "Agent-to-agent call" },
  { value: "a2a_discover", label: "Agent discovery" },
  { value: "cron", label: "Cron scheduler" },
] as const;

export const ACTIVITY_FILTERS: { key: ActivityFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "messages", label: "Messages" },
  { key: "tools", label: "Tools" },
  { key: "lifecycle", label: "Lifecycle" },
];

export const EVENT_TYPE_CONFIG: Record<string, { label: string; color: string; bg: string; icon: string; group: ActivityFilter }> = {
  message_received: { label: "Received", color: "text-blue-700", bg: "bg-blue-50 border-blue-200", icon: "↓", group: "messages" },
  message_sent: { label: "Sent", color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200", icon: "↑", group: "messages" },
  tool_call: { label: "Tool Call", color: "text-violet-700", bg: "bg-violet-50 border-violet-200", icon: "⚡", group: "tools" },
  tool_result: { label: "Result", color: "text-amber-700", bg: "bg-amber-50 border-amber-200", icon: "←", group: "tools" },
  agent_started: { label: "Started", color: "text-green-700", bg: "bg-green-50 border-green-200", icon: "●", group: "lifecycle" },
  agent_stopped: { label: "Stopped", color: "text-gray-600", bg: "bg-gray-50 border-gray-200", icon: "○", group: "lifecycle" },
  status: { label: "Status", color: "text-amber-600", bg: "bg-amber-50 border-amber-200", icon: "◐", group: "lifecycle" },
};

export const ACTIVITY_BUFFER_MAX = 500;
export const PROCESS_LOG_MAX = 1000;
