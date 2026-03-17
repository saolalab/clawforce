export type MCPServerConfig = {
  command: string;
  args: string[];
  env: Record<string, string>;
  url: string;
  headers?: Record<string, string>;
  /** When set, only these tool names are registered. Empty/undefined = all tools. */
  enabledTools?: string[];
};

export type MCPServerStatusInfo = {
  name: string;
  status: "connected" | "failed" | "skipped";
  tools: number;
  error?: string;
};

export type WebSearchConfig = {
  provider: "duckduckgo" | "brave" | "serpapi";
  brave_api_key: string;
  serpapi_api_key: string;
  max_results: number;
};

export type ShellPolicyConfig = {
  mode: "allow_all" | "deny_all" | "allowlist";
  allow: string[];
  deny: string[];
  relaxed?: boolean;
};

export type FaultToleranceConfig = {
  max_attempts: number;
  backoff_factor: number;
};

export type SoftwareCatalogEntry = {
  id: string;
  name: string;
  author: string;
  description: string;
  version: string;
  categories: string[];
  install: { type: string; package: string };
  run: { command: string; args: string[]; stdin?: boolean };
  required_env: string[];
  icon?: string;
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

export type SoftwareInstallResult = {
  ok: boolean;
  slug: string;
  message: string;
  logs: string;
  exit_code: number;
  verified: boolean;
};

export type SecretsConfig = {
  env: Record<string, string>;
};

export type ToolsConfig = {
  web: { search: WebSearchConfig };
  exec: { timeout: number; policy?: ShellPolicyConfig };
  restrict_to_workspace: boolean;
  ssrf_protection?: boolean;
  mcp_servers: Record<string, MCPServerConfig>;
  software?: Record<string, SoftwareInstalledEntry>;
};

export type SoftwareWarning = {
  key: string;
  name: string;
  command: string;
};

export type SecurityConfig = {
  docker?: {
    level?: "permissive" | "sandboxed";
  };
};

export type Agent = {
  id: string;
  name: string;
  description: string;
  model: string;
  status: string;
  status_message?: string;
  enabled: boolean;
  temperature: number;
  max_tokens: number;
  max_tool_iterations: number;
  memory_window: number;
  max_tool_output_chars: number;
  fault_tolerance?: FaultToleranceConfig;
  workspace: string;
  tools: ToolsConfig;
  channels: Record<string, Record<string, unknown>>;
  providers?: Record<string, Record<string, unknown>>;
  skills?: { disabled: string[] };
  heartbeat?: Record<string, unknown>;
  security?: SecurityConfig;
  color?: string;
  mcp_status?: Record<string, MCPServerStatusInfo>;
  software_warnings?: SoftwareWarning[];
  software_installing?: boolean;
  onboarding_completed?: boolean;
};

export type AgentSummary = {
  id: string;
  name: string;
  status: string;
  status_message?: string;
  color?: string;
  channels_enabled?: string[];
};

export type InboxEvent = {
  id: string;
  agent_id: string;
  agent_name: string;
  agent_color?: string;
  timestamp: string;
  event_type: string;
  content: string;
  tool_name?: string;
  result_status?: string;
  duration_ms?: number;
};

export type SkillsConfig = {
  disabled: string[];
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

export type MarketplaceSkill = {
  slug: string;
  name: string;
  description: string;
  version: string;
  author: string;
  downloads: number;
  categories?: string[];
  homepage?: string;
  repository?: string;
  required_env?: string[];
};

export type MCPRegistryServer = {
  id: string;
  slug: string;
  name: string;
  description: string;
  repository: string;
  homepage: string;
  version: string;
  license: string;
  author: string;
  verified: boolean;
  is_verified: boolean;
  downloads: number;
  created_at: string;
  updated_at: string;
  categories: string[];
  capabilities: string[];
  install_config: Record<string, unknown> | Record<string, unknown>[];
  required_env?: string[];
};

export type WorkspaceFiles = {
  files: string[];
};

export type PlanTask = {
  id: string;
  title: string;
  description: string;
  column_id: string;
  agent_id: string;
  position: number;
  created_at?: string;
  updated_at?: string;
};

export type PlanColumn = {
  id: string;
  title: string;
  position: number;
};

export type Plan = {
  id: string;
  name: string;
  description: string;
  status: string;
  columns: PlanColumn[];
  tasks: PlanTask[];
  agent_ids: string[];
  created_at: string;
  updated_at: string;
};

export type PlanArtifact = {
  id: string;
  task_id: string;
  name: string;
  content_type: string;
  content: string;
  file_path: string;
  size: number;
  created_at: string;
};

export type TaskComment = {
  id: string;
  task_id: string;
  author_type: "admin" | "agent";
  author_id: string;
  author_name: string;
  content: string;
  created_at: string;
};
