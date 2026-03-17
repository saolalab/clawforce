import { useState } from "react";
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

export function ToolsTab({ agent, updateTools, setTools }: { agent: Agent; updateTools: (p: Record<string, unknown>) => void; setTools: (t: ToolsCfg) => void }) {
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState<"stdio" | "http">("stdio");
  const [newCmd, setNewCmd] = useState("");
  const [newArgs, setNewArgs] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [newEnv, setNewEnv] = useState("");
  const [newHeaders, setNewHeaders] = useState("");
  const [newEnabledTools, setNewEnabledTools] = useState("");

  const tools = agent.tools;
  const mcpServers = tools.mcp_servers || {};

  function addServer() {
    if (!newName.trim()) return;
    const enabledToolsList = newEnabledTools
      .split(/[,\s]+/)
      .map((t) => t.trim())
      .filter(Boolean);
    const srv: MCPServer =
      newType === "stdio"
        ? {
          command: newCmd,
          args: newArgs.split(",").map((s) => s.trim()).filter(Boolean),
          env: Object.fromEntries(
            newEnv.split("\n").filter(Boolean).map((line) => {
              const [k, ...rest] = line.split("=");
              return [k.trim(), rest.join("=").trim()];
            }),
          ),
          url: "",
          ...(enabledToolsList.length > 0 && { enabledTools: enabledToolsList }),
        }
        : {
          command: "",
          args: [],
          env: {},
          url: newUrl,
          headers: Object.fromEntries(
            newHeaders.split("\n").filter(Boolean).map((line) => {
              const [k, ...rest] = line.split("=");
              return [k.trim(), rest.join("=").trim()];
            }),
          ),
          ...(enabledToolsList.length > 0 && { enabledTools: enabledToolsList }),
        };

    updateTools({ mcp_servers: { ...mcpServers, [newName.trim()]: srv } });
    resetForm();
  }

  function removeServer(name: string) {
    const next = { ...mcpServers };
    delete next[name];
    setTools({ ...tools, mcp_servers: next });
  }

  function resetForm() {
    setAdding(false);
    setNewName("");
    setNewCmd("");
    setNewArgs("");
    setNewUrl("");
    setNewEnv("");
    setNewHeaders("");
    setNewEnabledTools("");
    setNewType("stdio");
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
            return (
              <div key={name} className="flex items-start justify-between rounded-lg border border-claude-border bg-claude-bg p-2.5">
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
                <button onClick={() => removeServer(name)} className="ml-3 text-xs text-red-400 hover:text-red-600 transition-colors">
                  Remove
                </button>
              </div>
            );
          })}
        </div>

        {adding ? (
          <div className="mt-2 space-y-2.5 rounded-lg border border-claude-accent/30 bg-claude-accent-soft p-3">
            <div>
              <label className={css.label}>Server Name</label>
              <input className={css.input} value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="my-mcp-server" autoFocus />
            </div>

            <div className="flex gap-4">
              <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                <input type="radio" checked={newType === "stdio"} onChange={() => setNewType("stdio")} className="accent-claude-accent" />
                stdio
              </label>
              <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                <input type="radio" checked={newType === "http"} onChange={() => setNewType("http")} className="accent-claude-accent" />
                HTTP
              </label>
            </div>

            {newType === "stdio" ? (
              <>
                <div>
                  <label className={css.label}>Command</label>
                  <input className={css.input} value={newCmd} onChange={(e) => setNewCmd(e.target.value)} placeholder="npx" />
                </div>
                <div>
                  <label className={css.label}>Arguments (comma-separated)</label>
                  <input
                    className={css.input}
                    value={newArgs}
                    onChange={(e) => setNewArgs(e.target.value)}
                    placeholder="-y, @modelcontextprotocol/server-filesystem, /path"
                  />
                </div>
                <div>
                  <label className={css.label}>Environment Variables (KEY=VALUE, one per line)</label>
                  <textarea
                    className={`${css.input} resize-none font-mono`}
                    rows={2}
                    value={newEnv}
                    onChange={(e) => setNewEnv(e.target.value)}
                    placeholder="API_KEY=abc123"
                  />
                </div>
                <div>
                  <label className={css.label}>Enabled Tools (optional)</label>
                  <input
                    className={css.input}
                    value={newEnabledTools}
                    onChange={(e) => setNewEnabledTools(e.target.value)}
                    placeholder="Comma-separated. Leave empty for all tools. e.g. read_file, write_file"
                  />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className={css.label}>URL</label>
                  <input className={css.input} value={newUrl} onChange={(e) => setNewUrl(e.target.value)} placeholder="https://example.com/mcp" />
                </div>
                <div>
                  <label className={css.label}>Headers (KEY=VALUE, one per line)</label>
                  <textarea
                    className={`${css.input} resize-none font-mono`}
                    rows={2}
                    value={newHeaders}
                    onChange={(e) => setNewHeaders(e.target.value)}
                    placeholder="Authorization=Bearer token"
                  />
                </div>
                <div>
                  <label className={css.label}>Enabled Tools (optional)</label>
                  <input
                    className={css.input}
                    value={newEnabledTools}
                    onChange={(e) => setNewEnabledTools(e.target.value)}
                    placeholder="Comma-separated. Leave empty for all tools"
                  />
                </div>
              </>
            )}

            <div className="flex gap-2">
              <button
                onClick={addServer}
                disabled={!newName.trim()}
                className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover disabled:opacity-40`}
              >
                Add Server
              </button>
              <button onClick={resetForm} className={`${css.btn} text-claude-text-muted hover:text-claude-text-secondary`}>
                Cancel
              </button>
            </div>
          </div>
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
