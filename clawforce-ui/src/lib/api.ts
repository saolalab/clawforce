const LAUNCH_ENV_KEY = "launchEnv";
const API_BASE_CUSTOM_KEY = "apiBaseCustom";

export type LaunchEnv = "local" | "docker" | "custom";

export function getLaunchEnv(): LaunchEnv {
  const v = localStorage.getItem(LAUNCH_ENV_KEY);
  if (v === "docker" || v === "custom") return v;
  return "local";
}

export function setLaunchEnv(env: LaunchEnv, customBase?: string): void {
  localStorage.setItem(LAUNCH_ENV_KEY, env);
  if (env === "custom" && customBase != null) {
    localStorage.setItem(API_BASE_CUSTOM_KEY, customBase);
  }
}

export function getApiBaseCustom(): string {
  return localStorage.getItem(API_BASE_CUSTOM_KEY) || "";
}

export function getApiBase(): string {
  const env = getLaunchEnv();
  if (env === "local") return "";
  if (env === "docker") return "http://localhost:8080";
  return getApiBaseCustom().replace(/\/$/, "");
}

function getBase(): string {
  return getApiBase() + "/api";
}

function getToken(): string | null {
  return localStorage.getItem("token");
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getBase()}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...init?.headers },
  });
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith("/providers/")) {
      localStorage.removeItem("token");
      window.dispatchEvent(new Event("auth:expired"));
      throw new Error("Session expired");
    }
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch { /* ignore parse errors */ }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  const ct = res.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) return res.json();
  return res.text() as unknown as T;
}

function post<T = void>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
}

function put<T = void>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export type RuntimeBackendOption = { value: string; label: string };

export type DockerPreset = Record<string, unknown>;

export type RuntimeInfo = {
  runtime_type: string;
  runtime_label: string;
  running_count: number;
  running_agent_ids: string[];
  available_backends: RuntimeBackendOption[];
  data_root?: string | null;
  /** When runtime_type is docker: permissive, sandboxed, and privileged security presets (from server env). */
  docker_presets?: { permissive: DockerPreset; sandboxed: DockerPreset; privileged?: DockerPreset };
};

export const api = {
  auth: {
    streamToken: (): Promise<string> =>
      post<{ token: string }>("/auth/stream-token").then((r) => r.token),
    changePassword: (body: { current_password: string; new_password: string }) =>
      post<{ message: string }>("/auth/change-password", body),
  },
  runtime: {
    info: () => request<RuntimeInfo>("/runtime/info"),
    setBackend: (runtime_type: string) =>
      request<{ ok: boolean; runtime_type: string; runtime_label: string }>("/runtime/backend", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ runtime_type }),
      }),
  },
  templates: {
    list: () => request<{ value: string; label: string }[]>("/templates"),
    detail: (id: string) =>
      request<{
        value: string;
        label: string;
        profileFiles: { path: string; content: string }[];
        workspaceFiles: { path: string; content: string }[];
      }>(`/templates/${id}`),
  },
  claws: {
    list: () => request<import("./types").AgentSummary[]>("/agents"),
    create: (data: { name: string; description?: string; template?: string; color?: string }) =>
      post<import("./types").AgentSummary>("/agents", data),
  },
  agents: {
    get: (id: string) => request<import("./types").Agent>(`/agents/${id}`),
    update: (id: string, data: Partial<import("./types").Agent>) => put<import("./types").Agent>(`/agents/${id}`, data),
    delete: (id: string) => request<{ ok: boolean }>(`/agents/${id}`, { method: "DELETE" }),
    start: (id: string) => post(`/agents/${id}/start`),
    stop: (id: string) => post(`/agents/${id}/stop`),
    config: (id: string) => request<Record<string, unknown>>(`/agents/${id}/config`),
    updateConfig: (id: string, config: unknown) => put(`/agents/${id}/config`, config),
    variables: (id: string) => request<Record<string, string>>(`/agents/${id}/variables`),
    updateVariables: (id: string, payload: { variables: Record<string, string>; secret_keys: string[] }) =>
      put<Record<string, string>>(`/agents/${id}/variables`, payload),
    skills: (id: string) => request<import("./types").SkillInfo[]>(`/agents/${id}/skills`),
    installSkill: (id: string, slug: string, version?: string, env?: Record<string, string>) =>
      post<{ ok: boolean; slug: string; message: string }>(
        `/agents/${id}/skills/install`,
        { slug, version, env }
      ),
    uninstallSkill: (id: string, slug: string) =>
      post<{ ok: boolean; slug: string }>(`/agents/${id}/skills/uninstall`, { slug }),
    workspaceFiles: (id: string, root?: "workspace" | "profiles") =>
      request<{ files: string[]; agent_read_only: boolean }>(
        `/agents/${id}/workspace${root && root !== "workspace" ? `?root=${root}` : ""}`,
      ),
    workspaceFile: (id: string, path: string) => request<string>(`/agents/${id}/workspace/${path}`),
    downloadFileUrl: (id: string, path: string) =>
      `${getBase()}/agents/${id}/workspace/${path}?download=true`,
    downloadFolderZipUrl: (id: string, folderPath: string) =>
      `${getBase()}/agents/${id}/workspace-download/${folderPath}`,
    saveWorkspaceFile: (id: string, path: string, content: string) =>
      put(`/agents/${id}/workspace/${path}`, { content }),
    deleteWorkspaceFile: (id: string, path: string) =>
      request<{ ok: boolean }>(`/agents/${id}/workspace/${path}`, { method: "DELETE" }),
    renameWorkspaceFile: (id: string, path: string, newName: string) =>
      post<{ ok: boolean }>(`/agents/${id}/workspace/${path}/rename`, { new_name: newName }),
    moveWorkspaceFile: (id: string, srcPath: string, destPath: string) =>
      post<{ ok: boolean }>(`/agents/${id}/workspace/${srcPath}/move`, { dest_path: destPath }),
  },
  skills: {
    search: (q: string, limit = 20) =>
      request<import("./types").MarketplaceSkill[]>(`/skills/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  },
  mcpRegistry: {
    search: (q: string = "", limit = 50) =>
      request<import("./types").MCPRegistryServer[]>(
        `/mcp-registry/search?q=${encodeURIComponent(q)}&limit=${limit}`
      ),
    get: (serverId: string) =>
      request<import("./types").MCPRegistryServer>(`/mcp-registry/servers/${encodeURIComponent(serverId)}`),
    install: (agentId: string, config: {
      server_id: string;
      server_name: string;
      command?: string;
      args?: string[];
      env?: Record<string, string>;
      url?: string;
    }) =>
      post<{ ok: boolean; server_key: string; message: string }>(
        `/agents/${agentId}/mcp-servers/install`,
        config
      ),
  },
  mcp: {
    listServers: (agentId: string) =>
      request<{
        agent_id: string;
        agent_status: string;
        servers: Record<string, import("./types").MCPServerStatusInfo>;
      }>(`/agents/${agentId}/mcp-servers`),
    getTools: (agentId: string, serverKey: string) =>
      request<{
        agent_id: string;
        server_key: string;
        tools: Array<{ name: string; full_name: string; description: string; parameters?: any }>;
      }>(`/agents/${agentId}/mcp-servers/${encodeURIComponent(serverKey)}/tools`),
  },
  software: {
    catalog: () =>
      request<import("./types").SoftwareCatalogEntry[]>("/software/catalog"),
    get: (softwareId: string) =>
      request<import("./types").SoftwareCatalogEntry>(
        `/software/catalog/${encodeURIComponent(softwareId)}`
      ),
    install: (agentId: string, body: { software_id: string; env?: Record<string, string> }) =>
      post<import("./types").SoftwareInstallResult>(
        `/agents/${agentId}/software/install`,
        body
      ),
    uninstall: (agentId: string, body: { slug: string }) =>
      post<{ ok: boolean; slug: string; message: string }>(
        `/agents/${agentId}/software/uninstall`,
        body
      ),
    listCustom: () =>
      request<import("./types").SoftwareCatalogEntry[]>("/software/custom"),
    addCustom: (entry: import("./types").AddCustomSoftwarePayload) =>
      post<import("./types").SoftwareCatalogEntry>("/software/custom", entry),
    updateCustom: (softwareId: string, entry: import("./types").AddCustomSoftwarePayload) =>
      put<import("./types").SoftwareCatalogEntry>(`/software/custom/${encodeURIComponent(softwareId)}`, entry),
    deleteCustom: (softwareId: string) =>
      request<{ ok: boolean; id: string }>(
        `/software/custom/${encodeURIComponent(softwareId)}`,
        { method: "DELETE" }
      ),
  },
  plans: {
    list: () => request<import("./types").Plan[]>("/plans"),
    create: (data: { name: string; description?: string }) =>
      post<import("./types").Plan>("/plans", data),
    get: (id: string) => request<import("./types").Plan>(`/plans/${id}`),
    update: (id: string, data: Partial<import("./types").Plan>) => put<import("./types").Plan>(`/plans/${id}`, data),
    delete: (id: string) => request<{ ok: boolean }>(`/plans/${id}`, { method: "DELETE" }),
    addTask: (planId: string, data: { column_id: string; title?: string; description?: string; agent_id?: string }) =>
      post<import("./types").PlanTask>(`/plans/${planId}/tasks`, data),
    updateTask: (planId: string, taskId: string, data: Partial<import("./types").PlanTask>) =>
      put<import("./types").PlanTask>(`/plans/${planId}/tasks/${taskId}`, data),
    deleteTask: (planId: string, taskId: string) =>
      request<{ ok: boolean }>(`/plans/${planId}/tasks/${taskId}`, { method: "DELETE" }),
    listComments: (planId: string, taskId: string) =>
      request<import("./types").TaskComment[]>(`/plans/${planId}/tasks/${taskId}/comments`),
    addComment: (planId: string, taskId: string, content: string) =>
      post<import("./types").TaskComment>(`/plans/${planId}/tasks/${taskId}/comments`, { content }),
    deleteComment: (planId: string, commentId: string) =>
      request<{ ok: boolean }>(`/plans/${planId}/comments/${commentId}`, { method: "DELETE" }),
    assignAgent: (planId: string, agentId: string) =>
      post<{ ok: boolean }>(`/plans/${planId}/agents/${agentId}`),
    removeAgent: (planId: string, agentId: string) =>
      request<{ ok: boolean }>(`/plans/${planId}/agents/${agentId}`, { method: "DELETE" }),
    activate: async (planId: string): Promise<{ ok: boolean; status: string }> => {
      const res = await fetch(`${getBase()}/plans/${planId}/activate`, {
        method: "POST",
        headers: { ...authHeaders() },
      });
      const body = await res.json().catch(() => ({}));
      if (res.status === 409 && body.detail?.agents) {
        const e = new Error(body.detail?.message ?? "Agents not running") as Error & { detail?: { agents: string[]; message: string } };
        e.detail = { agents: body.detail.agents, message: body.detail.message ?? "" };
        throw e;
      }
      if (!res.ok) throw new Error(body.detail?.message ?? body.detail ?? res.statusText);
      return body;
    },
    deactivate: (planId: string) => post<{ ok: boolean; status: string }>(`/plans/${planId}/deactivate`),
    complete: (planId: string) => post<{ ok: boolean; status: string }>(`/plans/${planId}/complete`),
    assistant: (planId: string, agentId: string, message: string) =>
      post<{ ok: boolean; agent_id: string; response: string }>(`/plans/${planId}/assistant`, { agent_id: agentId, message }),
    listArtifacts: (planId: string, taskId?: string) =>
      request<import("./types").PlanArtifact[]>(
        taskId ? `/plans/${planId}/artifacts?task_id=${encodeURIComponent(taskId)}` : `/plans/${planId}/artifacts`,
      ),
    uploadArtifact: async (planId: string, file: File): Promise<import("./types").PlanArtifact> => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${getBase()}/plans/${planId}/artifacts/upload`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });
      if (!res.ok) {
        let detail = res.statusText;
        try { const b = await res.json(); if (b.detail) detail = b.detail; } catch { /* ignore */ }
        throw new Error(`API ${res.status}: ${detail}`);
      }
      return res.json();
    },
    downloadArtifactUrl: (planId: string, artifactId: string) =>
      `${getBase()}/plans/${planId}/artifacts/${artifactId}/download`,
    deleteArtifact: (planId: string, artifactId: string) =>
      request<{ ok: boolean }>(`/plans/${planId}/artifacts/${artifactId}`, { method: "DELETE" }),
    renameArtifact: (planId: string, artifactId: string, newName: string) =>
      post<import("./types").PlanArtifact>(`/plans/${planId}/artifacts/${artifactId}/rename`, { new_name: newName }),
    moveArtifact: (planId: string, artifactId: string, taskId: string) =>
      post<import("./types").PlanArtifact>(`/plans/${planId}/artifacts/${artifactId}/move`, { task_id: taskId }),
    // Workspace filesystem
    workspaceFiles: (planId: string) =>
      request<{ files: string[]; root: string }>(`/plans/${planId}/workspace`),
    workspaceFile: (planId: string, path: string) =>
      request<string>(`/plans/${planId}/workspace/${path}`),
    downloadFileUrl: (planId: string, path: string) =>
      `${getBase()}/plans/${planId}/workspace/${path}?download=true`,
    downloadFolderZipUrl: (planId: string, folderPath: string) =>
      `${getBase()}/plans/${planId}/workspace-download/${folderPath}`,
    saveWorkspaceFile: (planId: string, path: string, content: string) =>
      put(`/plans/${planId}/workspace/${path}`, { content }),
    uploadWorkspaceFile: async (planId: string, file: File, path?: string): Promise<{ ok: boolean; path: string }> => {
      const form = new FormData();
      form.append("file", file);
      const url = path
        ? `${getBase()}/plans/${planId}/workspace/upload?path=${encodeURIComponent(path)}`
        : `${getBase()}/plans/${planId}/workspace/upload`;
      const res = await fetch(url, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });
      if (!res.ok) {
        let detail = res.statusText;
        try { const b = await res.json(); if (b.detail) detail = b.detail; } catch { /* ignore */ }
        throw new Error(`API ${res.status}: ${detail}`);
      }
      return res.json();
    },
    deleteWorkspaceFile: (planId: string, path: string) =>
      request<{ ok: boolean }>(`/plans/${planId}/workspace/${path}`, { method: "DELETE" }),
    renameWorkspaceFile: (planId: string, path: string, newName: string) =>
      post<{ ok: boolean }>(`/plans/${planId}/workspace/${path}/rename`, { new_name: newName }),
    moveWorkspaceFile: (planId: string, srcPath: string, destPath: string) =>
      post<{ ok: boolean }>(`/plans/${planId}/workspace/${srcPath}/move`, { dest_path: destPath }),
    createWorkspaceFolder: (planId: string, path: string) =>
      post<{ ok: boolean }>(`/plans/${planId}/workspace-folder/${path}`),
  },
  providers: {
    listModels: (provider: string, apiKey: string, agentId?: string, apiBase?: string) =>
      post<{ provider: string; prefix: string; models: { id: string; name: string }[] }>(
        "/providers/models",
        { provider, api_key: apiKey, agent_id: agentId || "", api_base: apiBase || "" },
      ),
    oauthStatus: (provider: string, agentId?: string) =>
      request<{ provider: string; authorized: boolean; account_id?: string }>(
        `/providers/oauth/${encodeURIComponent(provider)}/status${agentId ? `?agent_id=${encodeURIComponent(agentId)}` : ""}`,
      ),
    oauthAuthorize: (provider: string, agentId?: string) =>
      post<{ auth_url: string }>(
        `/providers/oauth/${encodeURIComponent(provider)}/authorize`,
        { agent_id: agentId || "" },
      ),
  },
  admin: {
    getSettings: () =>
      request<Record<string, any>>("/admin/settings"),
    updateSettings: (settings: Record<string, any>) =>
      put<Record<string, any>>("/admin/settings", settings),
  },
};
