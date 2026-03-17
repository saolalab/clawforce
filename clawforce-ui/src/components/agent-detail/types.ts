export type MCPServer = {
  command: string;
  args: string[];
  env: Record<string, string>;
  url: string;
  headers?: Record<string, string>;
  /** When set, only these tool names are registered. Empty/undefined = all tools. */
  enabledTools?: string[];
};

export type ApprovalCfg = {
  default_mode: string;
  per_tool: Record<string, string>;
  timeout_seconds: number;
};

export type SoftwareInstalledEntry = {
  name: string;
  description: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  installed_via: string;
  package: string;
  stdin?: boolean;
  installed_at?: string;
  verified?: boolean;
};

export type ToolsCfg = {
  web: { search: { provider: "duckduckgo" | "brave" | "serpapi"; brave_api_key: string; serpapi_api_key: string; max_results: number } };
  exec: { timeout: number; policy?: { mode: "allow_all" | "deny_all" | "allowlist"; allow: string[]; deny: string[]; relaxed?: boolean } };
  restrict_to_workspace: boolean;
  ssrf_protection?: boolean;
  mcp_servers: Record<string, MCPServer>;
  software?: Record<string, SoftwareInstalledEntry>;
  approval?: ApprovalCfg;
};

export type HeartbeatCfg = {
  enabled: boolean;
  interval_s: number;
  cron_expr: string;
  timezone: string;
};

export type SkillsCfg = {
  disabled: string[];
};

export type MCPStatusInfo = {
  name: string;
  status: "connected" | "failed" | "skipped";
  tools: number;
  error?: string;
};

export type SecurityCfg = {
  docker?: { level?: "permissive" | "sandboxed" };
};

export type Agent = {
  id: string;
  name: string;
  description: string;
  color?: string;
  model: string;
  status: string;
  status_message?: string;
  enabled: boolean;
  temperature: number;
  max_tokens: number;
  max_tool_iterations: number;
  memory_window: number;
  fault_tolerance?: { max_attempts: number; backoff_factor: number };
  workspace: string;
  tools: ToolsCfg;
  skills?: SkillsCfg;
  channels: Record<string, Record<string, unknown>>;
  providers?: Record<string, Record<string, unknown>>;
  heartbeat?: HeartbeatCfg;
  security?: SecurityCfg;
  mcp_status?: Record<string, MCPStatusInfo>;
  software_warnings?: { key: string; name: string; command: string }[];
  software_installing?: boolean;
  onboarding_completed?: boolean;
};

export type MainTab = "workspace" | "jobs" | "logs" | "settings";
export type SettingsTab = "general" | "variables" | "channels" | "tools" | "skills" | "software";

export type FieldDef = { name: string; label: string; type: "text" | "password" | "number" | "toggle" | "tags"; placeholder?: string };

export type TreeNode = { name: string; path: string; isDir: boolean; children: TreeNode[] };

export type LogView = "activity" | "process";

export type ActivityEntry = {
  ts: string;
  type: string;
  content: string;
  channel: string;
  toolName?: string;
  resultStatus?: string;
  durationMs?: number;
  eventId?: string;
};

export type ActivityFilter = "all" | "messages" | "tools" | "lifecycle";

export type CronJobData = {
  id: string;
  name: string;
  enabled: boolean;
  schedule: { kind: string; atMs?: number; everyMs?: number; expr?: string; tz?: string };
  payload: { kind: string; message: string; deliver?: boolean; channel?: string; to?: string };
  state: { nextRunAtMs?: number; lastRunAtMs?: number; lastStatus?: string; lastError?: string };
  createdAtMs: number;
  deleteAfterRun?: boolean;
};

export type SkillInfo = {
  name: string;
  description: string;
  source: "builtin" | "workspace";
  emoji: string;
  enabled: boolean;
  available: boolean;
  always: boolean;
};

export type ProviderDef = { field: string; label: string; keywords: string[]; oauth?: boolean };

export type WsViewMode = "edit" | "preview";
