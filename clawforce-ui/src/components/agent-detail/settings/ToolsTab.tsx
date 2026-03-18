import { useState } from "react";
import { api } from "../../../lib/api";
import { css, BUILTIN_TOOLS } from "../constants";
import { Section, Toggle } from "../ui/Section";
import type { Agent, ApprovalCfg, MCPServer, ToolsCfg } from "../types";

function ToolApprovalSection({ tools, setTools }: { tools: ToolsCfg; setTools: (t: ToolsCfg) => void }) {
  const approval = tools.approval ?? { default_mode: "always_run", per_tool: {}, timeout_seconds: 120 };
  const perToolMap = approval.per_tool ?? (approval as { perTool?: Record<string, string> }).perTool ?? {};
  const [showPerTool, setShowPerTool] = useState(false);

  const allTools: { value: string; label: string }[] = [...BUILTIN_TOOLS];

  function setApproval(patch: Partial<ApprovalCfg>) {
    setTools({ ...tools, approval: { ...approval, ...patch } });
  }

  function setPerTool(toolName: string, mode: string) {
    const next = { ...perToolMap };
    if (mode === approval.default_mode) {
      delete next[toolName];
    } else {
      next[toolName] = mode;
    }
    setApproval({ per_tool: next });
  }

  const overrideCount = Object.keys(perToolMap).length;
  const enabled = (approval.default_mode || "always_run") === "ask_before_run";

  return (
    <Section title="Tool Approval">
      <div className="space-y-3">
        <div>
          <Toggle
            checked={enabled}
            onChange={(v) => setApproval({ default_mode: v ? "ask_before_run" : "always_run" })}
            label="Require approval before running tools"
          />
          <p className="text-[10px] text-claude-text-muted mt-1.5 ml-[46px]">
            When enabled, the agent asks the user for permission before executing each tool call.
          </p>
        </div>

        {enabled && (
          <div className="ml-[46px]">
            <label className={css.label}>Approval timeout (seconds)</label>
            <input
              type="number"
              className={css.input}
              style={{ maxWidth: "10rem" }}
              value={approval.timeout_seconds ?? 120}
              onChange={(e) => setApproval({ timeout_seconds: parseInt(e.target.value) || 120 })}
            />
            <p className="text-[10px] text-claude-text-muted mt-1">
              If the user doesn't respond within this time, the tool call is denied.
            </p>
          </div>
        )}

        <div>
          <button
            type="button"
            onClick={() => setShowPerTool(!showPerTool)}
            className="flex items-center gap-1.5 text-xs text-claude-text-muted hover:text-claude-text-secondary transition-colors"
          >
            <svg className={`h-3 w-3 transition-transform ${showPerTool ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Per-tool overrides{overrideCount > 0 && ` (${overrideCount})`}
          </button>

          {showPerTool && (
            <div className="mt-2 space-y-1.5">
              <p className="text-[10px] text-claude-text-muted mb-1">
                Override the default for specific tools. Tools not listed here use the default behavior.
              </p>
              {allTools.map((t) => {
                const effective = perToolMap[t.value] || approval.default_mode || "always_run";
                const isOverridden = t.value in perToolMap;
                return (
                  <div key={t.value} className="flex items-center justify-between gap-3 rounded-md border border-claude-border bg-claude-bg px-2.5 py-1.5">
                    <span className={`text-xs ${isOverridden ? "text-claude-text-primary font-medium" : "text-claude-text-muted"}`}>
                      {t.label}
                    </span>
                    <select
                      className="rounded border border-claude-border bg-claude-surface px-2 py-1 text-[11px] text-claude-text-secondary"
                      value={effective}
                      onChange={(e) => setPerTool(t.value, e.target.value)}
                    >
                      <option value="always_run">Always allow</option>
                      <option value="ask_before_run">Ask permission</option>
                    </select>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Section>
  );
}

function serializeKV(obj: Record<string, string> | undefined): string {
  if (!obj) return "";
  return Object.entries(obj).map(([k, v]) => `${k}=${v}`).join("\n");
}

function parseKV(text: string): Record<string, string> {
  return Object.fromEntries(
    text.split("\n").filter(Boolean).map((line) => {
      const [k, ...rest] = line.split("=");
      return [k.trim(), rest.join("=").trim()];
    }),
  );
}

type EditState = {
  name: string;
  type: "stdio" | "http";
  cmd: string;
  args: string;
  url: string;
  env: string;
  headers: string;
  enabledTools: string;
};

function mcpServerToEditState(name: string, srv: import("../types").MCPServer): EditState {
  return {
    name,
    type: srv.url ? "http" : "stdio",
    cmd: srv.command || "",
    args: (srv.args || []).join(", "),
    url: srv.url || "",
    env: serializeKV(srv.env),
    headers: serializeKV(srv.headers),
    enabledTools: (srv.enabledTools || []).join(", "),
  };
}

function editStateToServer(s: EditState): import("../types").MCPServer {
  const enabledToolsList = s.enabledTools.split(/[,\s]+/).map((t) => t.trim()).filter(Boolean);
  if (s.type === "stdio") {
    return {
      command: s.cmd,
      args: s.args.split(",").map((a) => a.trim()).filter(Boolean),
      env: parseKV(s.env),
      url: "",
      ...(enabledToolsList.length > 0 && { enabledTools: enabledToolsList }),
    };
  }
  return {
    command: "",
    args: [],
    env: {},
    url: s.url,
    headers: parseKV(s.headers),
    ...(enabledToolsList.length > 0 && { enabledTools: enabledToolsList }),
  };
}

function McpToolPicker({
  agentId,
  serverKey,
  enabledTools,
  onChange,
}: {
  agentId: string;
  serverKey: string;
  enabledTools: string;
  onChange: (v: string) => void;
}) {
  const [tools, setTools] = useState<{ name: string; description: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fetched, setFetched] = useState(false);

  const selected = new Set(
    enabledTools.split(/[,\s]+/).map((t) => t.trim()).filter(Boolean)
  );

  function toggle(name: string) {
    const next = new Set(selected);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    onChange([...next].join(", "));
  }

  function fetchTools() {
    if (!agentId || !serverKey) return;
    setLoading(true);
    setError("");
    api.mcp.getTools(agentId, serverKey)
      .then((r) => {
        setTools(r.tools.map((t) => ({ name: t.name, description: t.description })));
        setFetched(true);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }

  if (!agentId || !serverKey) {
    return (
      <div>
        <label className={css.label}>Enabled Tools</label>
        <input className={css.input} value={enabledTools} onChange={(e) => onChange(e.target.value)} placeholder="Leave empty for all tools. e.g. read_file, write_file" />
        <p className="mt-1 text-[10px] text-claude-text-muted">Save the agent first to pick tools interactively.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className={css.label}>
          Enabled Tools
          {selected.size > 0 && (
            <span className="ml-1.5 text-[10px] font-normal text-claude-accent">
              {selected.size} of {fetched ? tools.length : "?"} selected
            </span>
          )}
        </label>
        <div className="flex items-center gap-2">
          {fetched && tools.length > 0 && (
            <>
              <button type="button" onClick={() => onChange(tools.map((t) => t.name).join(", "))} className="text-[10px] text-claude-text-muted hover:text-claude-accent transition-colors">
                All
              </button>
              <button type="button" onClick={() => onChange("")} className="text-[10px] text-claude-text-muted hover:text-claude-accent transition-colors">
                None
              </button>
            </>
          )}
          <button
            type="button"
            onClick={fetchTools}
            disabled={loading}
            className="text-[10px] text-claude-accent hover:underline disabled:opacity-50"
          >
            {loading ? "Loading…" : fetched ? "Refresh" : "Load tools"}
          </button>
        </div>
      </div>

      {error && <p className="text-[10px] text-red-500 mb-1">{error}</p>}

      {!fetched ? (
        <p className="text-[10px] text-claude-text-muted">
          {selected.size > 0
            ? `${selected.size} tool(s) configured. Click "Load tools" to see and edit them.`
            : 'Click "Load tools" to see available tools (agent must be running).'}
        </p>
      ) : tools.length === 0 ? (
        <p className="text-[10px] text-claude-text-muted">No tools found.</p>
      ) : (
        <div className="max-h-48 overflow-y-auto rounded-lg border border-claude-border bg-claude-bg divide-y divide-claude-border/50">
          {tools.map((t) => (
            <label key={t.name} className="flex items-start gap-2.5 px-2.5 py-1.5 cursor-pointer hover:bg-claude-surface transition-colors">
              <input
                type="checkbox"
                checked={selected.size === 0 || selected.has(t.name)}
                onChange={() => {
                  if (selected.size === 0) {
                    // "all" → deselect this one means enable all others
                    onChange(tools.filter((x) => x.name !== t.name).map((x) => x.name).join(", "));
                  } else {
                    toggle(t.name);
                  }
                }}
                className="mt-0.5 accent-claude-accent shrink-0"
              />
              <div className="min-w-0">
                <span className="text-xs font-mono text-claude-text-primary">{t.name}</span>
                {t.description && (
                  <p className="text-[10px] text-claude-text-muted truncate">{t.description}</p>
                )}
              </div>
            </label>
          ))}
        </div>
      )}
      {fetched && selected.size === 0 && (
        <p className="mt-1 text-[10px] text-claude-text-muted">All tools enabled (none filtered).</p>
      )}
    </div>
  );
}

function McpServerEditForm({
  agentId,
  initial,
  onSave,
  onCancel,
  isNew,
}: {
  agentId: string;
  initial: EditState;
  onSave: (name: string, srv: import("../types").MCPServer) => void;
  onCancel: () => void;
  isNew: boolean;
}) {
  const [s, setS] = useState<EditState>(initial);
  const patch = (p: Partial<EditState>) => setS((prev) => ({ ...prev, ...p }));

  return (
    <div className="mt-2 space-y-2.5 rounded-lg border border-claude-accent/30 bg-claude-accent-soft p-3">
      {isNew && (
        <div>
          <label className={css.label}>Server Name</label>
          <input className={css.input} value={s.name} onChange={(e) => patch({ name: e.target.value })} placeholder="my-mcp-server" autoFocus />
        </div>
      )}

      <div className="flex gap-4">
        <label className="flex items-center gap-1.5 text-sm cursor-pointer">
          <input type="radio" checked={s.type === "stdio"} onChange={() => patch({ type: "stdio" })} className="accent-claude-accent" />
          stdio
        </label>
        <label className="flex items-center gap-1.5 text-sm cursor-pointer">
          <input type="radio" checked={s.type === "http"} onChange={() => patch({ type: "http" })} className="accent-claude-accent" />
          HTTP
        </label>
      </div>

      {s.type === "stdio" ? (
        <>
          <div>
            <label className={css.label}>Command</label>
            <input className={css.input} value={s.cmd} onChange={(e) => patch({ cmd: e.target.value })} placeholder="npx" />
          </div>
          <div>
            <label className={css.label}>Arguments (comma-separated)</label>
            <input className={css.input} value={s.args} onChange={(e) => patch({ args: e.target.value })} placeholder="-y, @modelcontextprotocol/server-filesystem, /path" />
          </div>
          <div>
            <label className={css.label}>Environment Variables (KEY=VALUE, one per line)</label>
            <textarea className={`${css.input} resize-none font-mono`} rows={2} value={s.env} onChange={(e) => patch({ env: e.target.value })} placeholder="API_KEY=abc123" />
          </div>
        </>
      ) : (
        <>
          <div>
            <label className={css.label}>URL</label>
            <input className={css.input} value={s.url} onChange={(e) => patch({ url: e.target.value })} placeholder="https://example.com/mcp" />
          </div>
          <div>
            <label className={css.label}>Headers (KEY=VALUE, one per line)</label>
            <textarea
              className={`${css.input} resize-none font-mono`}
              rows={3}
              value={s.headers}
              onChange={(e) => patch({ headers: e.target.value })}
              placeholder={"Authorization=Bearer <token>\nX-Api-Key=your-key"}
            />
            <p className="mt-1 text-[10px] text-claude-text-muted">
              For OAuth: <code className="font-mono">Authorization=Bearer &lt;token&gt;</code>
            </p>
          </div>
        </>
      )}

      <McpToolPicker
        agentId={agentId}
        serverKey={isNew ? "" : s.name}
        enabledTools={s.enabledTools}
        onChange={(v) => patch({ enabledTools: v })}
      />

      <div className="flex gap-2">
        <button
          onClick={() => { if (isNew ? s.name.trim() : true) onSave(s.name.trim(), editStateToServer(s)); }}
          disabled={isNew && !s.name.trim()}
          className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover disabled:opacity-40`}
        >
          {isNew ? "Add Server" : "Save Changes"}
        </button>
        <button onClick={onCancel} className={`${css.btn} text-claude-text-muted hover:text-claude-text-secondary`}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export function ToolsTab({ agentId, agent, updateTools, setTools }: { agentId: string; agent: Agent; updateTools: (p: Record<string, unknown>) => void; setTools: (t: ToolsCfg) => void }) {
  const [adding, setAdding] = useState(false);
  const [editingServer, setEditingServer] = useState<string | null>(null);

  const tools = agent.tools;
  const mcpServers = tools.mcp_servers || {};

  function saveServer(name: string, srv: MCPServer) {
    updateTools({ mcp_servers: { ...mcpServers, [name]: srv } });
    setAdding(false);
    setEditingServer(null);
  }

  function removeServer(name: string) {
    const next = { ...mcpServers };
    delete next[name];
    setTools({ ...tools, mcp_servers: next });
  }

  return (
    <div className="space-y-3">
      <Section title="Web Search">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className={css.label}>Provider</label>
            <select
              className={css.input}
              value={tools.web?.search?.provider ?? "duckduckgo"}
              onChange={(e) => updateTools({ web: { search: { provider: e.target.value } } })}
            >
              <option value="duckduckgo">DuckDuckGo (no key required)</option>
              <option value="brave">Brave Search</option>
              <option value="serpapi">SerpAPI (Google)</option>
            </select>
          </div>
          {(tools.web?.search?.provider ?? "duckduckgo") !== "duckduckgo" && (
            <div>
              <label className={css.label}>
                {(tools.web?.search?.provider ?? "duckduckgo") === "serpapi" ? "SerpAPI Key" : "Brave API Key"}
              </label>
              {(tools.web?.search?.provider ?? "duckduckgo") === "serpapi" ? (
                <input
                  className={css.input}
                  type="password"
                  value={tools.web?.search?.serpapi_api_key ?? ""}
                  onChange={(e) => updateTools({ web: { search: { serpapi_api_key: e.target.value } } })}
                  placeholder="SerpAPI key"
                />
              ) : (
                <input
                  className={css.input}
                  type="password"
                  value={tools.web?.search?.brave_api_key ?? ""}
                  onChange={(e) => updateTools({ web: { search: { brave_api_key: e.target.value } } })}
                  placeholder="Brave Search API key"
                />
              )}
            </div>
          )}
          <div>
            <label className={css.label}>Max Results</label>
            <input
              type="number"
              className={css.input}
              value={tools.web?.search?.max_results ?? 5}
              onChange={(e) => updateTools({ web: { search: { max_results: parseInt(e.target.value) || 5 } } })}
            />
          </div>
        </div>
        <div className="mt-3 flex items-end pb-0.5">
          <Toggle
            checked={tools.ssrf_protection ?? true}
            onChange={(v) => updateTools({ ssrf_protection: v })}
            label="SSRF protection (block private/local URLs in web_fetch)"
          />
        </div>
      </Section>

      <Section title="MCP Servers">
        {Object.keys(mcpServers).length === 0 && !adding && (
          <p className="text-sm text-claude-text-muted mb-2">No MCP servers configured yet.</p>
        )}

        <div className="space-y-2">
          {Object.entries(mcpServers).map(([name, srv]) => {
            const st = agent.mcp_status?.[name];
            const isEditing = editingServer === name;
            return (
              <div key={name}>
                <div className="flex items-start justify-between rounded-lg border border-claude-border bg-claude-bg p-2.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-claude-text-primary">{name}</span>
                      <span
                        className={`rounded px-1.5 py-px text-[10px] font-medium ${srv.url
                            ? "bg-blue-50 text-blue-700 ring-1 ring-blue-200"
                            : "bg-purple-50 text-purple-700 ring-1 ring-purple-200"
                          }`}
                      >
                        {srv.url ? "HTTP" : "stdio"}
                      </span>
                      {st && (
                        <span
                          className={`rounded px-1.5 py-px text-[10px] font-medium ${st.status === "connected"
                              ? "bg-green-50 text-green-700 ring-1 ring-green-200"
                              : st.status === "failed"
                                ? "bg-red-50 text-red-700 ring-1 ring-red-200"
                                : "bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200"
                            }`}
                          title={st.error || undefined}
                        >
                          {st.status === "connected" ? `connected (${st.tools} tools)` : st.status}
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 truncate text-xs text-claude-text-muted font-mono">
                      {srv.url || `${srv.command} ${(srv.args || []).join(" ")}`}
                    </p>
                    {st?.status === "failed" && st.error && (
                      <p className="mt-0.5 text-xs text-red-500 truncate" title={st.error}>
                        {st.error}
                      </p>
                    )}
                  </div>
                  <div className="ml-3 flex items-center gap-2.5 shrink-0">
                    <button
                      onClick={() => setEditingServer(isEditing ? null : name)}
                      className="text-xs text-claude-text-muted hover:text-claude-accent transition-colors"
                    >
                      {isEditing ? "Cancel" : "Edit"}
                    </button>
                    <button onClick={() => removeServer(name)} className="text-xs text-red-400 hover:text-red-600 transition-colors">
                      Remove
                    </button>
                  </div>
                </div>
                {isEditing && (
                  <McpServerEditForm
                    agentId={agentId}
                    initial={mcpServerToEditState(name, srv)}
                    onSave={(_name, updated) => saveServer(name, updated)}
                    onCancel={() => setEditingServer(null)}
                    isNew={false}
                  />
                )}
              </div>
            );
          })}
        </div>

        {adding ? (
          <McpServerEditForm
            agentId={agentId}
            initial={{ name: "", type: "stdio", cmd: "", args: "", url: "", env: "", headers: "", enabledTools: "" }}
            onSave={saveServer}
            onCancel={() => setAdding(false)}
            isNew={true}
          />
        ) : (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="mt-2 w-full cursor-pointer rounded-lg border border-dashed border-claude-border-strong px-3 py-2.5 text-sm font-medium text-claude-text-muted transition-colors hover:border-claude-accent hover:text-claude-accent hover:bg-claude-accent-soft active:bg-claude-accent-soft"
          >
            + Add MCP Server
          </button>
        )}
      </Section>

      <ToolApprovalSection tools={tools} setTools={setTools} />
    </div>
  );
}
