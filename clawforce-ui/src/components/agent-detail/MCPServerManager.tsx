import { useState } from "react";
import { Button } from "../ui";
import type { MCPServerConfig, MCPServerStatusInfo } from "../../lib/types";

interface MCPServerManagerProps {
  servers: Record<string, MCPServerConfig>;
  serverStatus: Record<string, MCPServerStatusInfo>;
  registryServers: Array<{ id: string; name: string; description: string }>;
  isLoading: boolean;
  onAddServer: (name: string, config: MCPServerConfig) => void;
  onRemoveServer: (name: string) => void;
  onUpdateServer: (name: string, config: MCPServerConfig) => void;
}

/**
 * MCPServerManager allows configuration of MCP (Model Context Protocol) servers.
 * Supports both stdio-based and HTTP-based MCP servers.
 */
export function MCPServerManager({
  servers,
  serverStatus,
  isLoading,
  onAddServer,
  onRemoveServer,
  onUpdateServer,
}: MCPServerManagerProps) {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingServer, setEditingServer] = useState<string | null>(null);
  const [newServer, setNewServer] = useState<{
    name: string;
    type: "stdio" | "http";
    command: string;
    args: string;
    url: string;
    env: string;
    enabledTools: string;
  }>({
    name: "",
    type: "stdio",
    command: "",
    args: "",
    url: "",
    env: "",
    enabledTools: "",
  });

  const parseEnabledTools = (s: string): string[] | undefined => {
    const list = s.split(/[,\s]+/).map((t) => t.trim()).filter(Boolean);
    return list.length > 0 ? list : undefined;
  };

  const formatEnabledTools = (tools: string[] | undefined): string =>
    tools?.join(", ") ?? "";

  const handleAdd = () => {
    const baseConfig =
      newServer.type === "stdio"
        ? {
            command: newServer.command,
            args: newServer.args.split(/\s+/).filter(Boolean),
            env: parseEnv(newServer.env),
            url: "",
          }
        : {
            command: "",
            args: [],
            env: {},
            url: newServer.url,
          };
    const enabledTools = parseEnabledTools(newServer.enabledTools);
    const config: MCPServerConfig = { ...baseConfig, ...(enabledTools && { enabledTools }) };

    onAddServer(newServer.name, config);
    setShowAddDialog(false);
    setNewServer({ name: "", type: "stdio", command: "", args: "", url: "", env: "", enabledTools: "" });
  };

  const parseEnv = (envString: string): Record<string, string> => {
    const env: Record<string, string> = {};
    envString.split("\n").forEach((line) => {
      const match = line.match(/^([^=]+)=(.*)$/);
      if (match) {
        env[match[1].trim()] = match[2].trim();
      }
    });
    return env;
  };

  const formatEnv = (env: Record<string, string>): string => {
    return Object.entries(env)
      .map(([key, value]) => `${key}=${value}`)
      .join("\n");
  };

  const getStatusIcon = (status: string | undefined) => {
    switch (status) {
      case "connected":
        return <span className="text-green-500">●</span>;
      case "failed":
        return <span className="text-red-500">●</span>;
      case "skipped":
        return <span className="text-gray-400">○</span>;
      default:
        return <span className="text-amber-500 animate-pulse">●</span>;
    }
  };

  if (isLoading) {
    return (
      <div className="bg-claude-input rounded-xl border border-claude-border p-4">
        <p className="text-claude-text-secondary">Loading MCP servers...</p>
      </div>
    );
  }

  return (
    <div className="bg-claude-input rounded-xl border border-claude-border">
      <div className="px-4 py-3 border-b border-claude-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-claude-text-primary">MCP Servers</h3>
          <p className="text-xs text-claude-text-muted mt-0.5">Model Context Protocol servers extend agent capabilities</p>
        </div>
        <Button size="sm" onClick={() => setShowAddDialog(true)}>
          Add Server
        </Button>
      </div>

      <div className="divide-y divide-claude-border">
        {Object.entries(servers).length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-claude-text-secondary text-sm">No MCP servers configured</p>
            <p className="text-claude-text-muted text-xs mt-1">Add a server to extend agent capabilities with custom tools</p>
          </div>
        ) : (
          Object.entries(servers).map(([name, config]) => {
            const status = serverStatus[name];
            const isEditing = editingServer === name;

            return (
              <div key={name} className="px-4 py-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(status?.status)}
                      <span className="font-medium text-claude-text-primary">{name}</span>
                      {status?.tools && (
                        <span className="text-xs text-claude-text-muted">({status.tools} tools)</span>
                      )}
                    </div>
                    <p className="text-xs text-claude-text-secondary mt-1">
                      {config.command ? `${config.command} ${config.args.join(" ")}` : config.url}
                    </p>
                    {status?.error && (
                      <p className="text-xs text-red-600 mt-1">Error: {status.error}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setEditingServer(isEditing ? null : name)}>
                      {isEditing ? "Done" : "Edit"}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onRemoveServer(name)}>
                      Remove
                    </Button>
                  </div>
                </div>

                {isEditing && (
                  <div className="mt-3 p-3 bg-claude-surface rounded-lg space-y-3">
                    <div>
                      <label className="block text-xs text-claude-text-muted mb-1">Command</label>
                      <input
                        type="text"
                        value={config.command}
                        onChange={(e) => onUpdateServer(name, { ...config, command: e.target.value })}
                        className="w-full px-2 py-1.5 text-sm border border-claude-border rounded bg-claude-bg"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-claude-text-muted mb-1">Arguments (space-separated)</label>
                      <input
                        type="text"
                        value={config.args.join(" ")}
                        onChange={(e) =>
                          onUpdateServer(name, { ...config, args: e.target.value.split(/\s+/).filter(Boolean) })
                        }
                        className="w-full px-2 py-1.5 text-sm border border-claude-border rounded bg-claude-bg"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-claude-text-muted mb-1">Environment Variables (KEY=value per line)</label>
                      <textarea
                        value={formatEnv(config.env)}
                        onChange={(e) => onUpdateServer(name, { ...config, env: parseEnv(e.target.value) })}
                        rows={3}
                        className="w-full px-2 py-1.5 text-sm border border-claude-border rounded bg-claude-bg font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-claude-text-muted mb-1">Enabled Tools (optional, comma-separated)</label>
                      <input
                        type="text"
                        value={formatEnabledTools(config.enabledTools)}
                        onChange={(e) => {
                          const tools = parseEnabledTools(e.target.value);
                          onUpdateServer(name, { ...config, enabledTools: tools });
                        }}
                        placeholder="Leave empty for all tools. e.g. read_file, write_file"
                        className="w-full px-2 py-1.5 text-sm border border-claude-border rounded bg-claude-bg"
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Add Server Dialog */}
      {showAddDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-claude-bg rounded-xl p-6 w-[500px] max-h-[90vh] overflow-y-auto">
            <h3 className="font-semibold text-claude-text-primary mb-4">Add MCP Server</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-claude-text-muted mb-1">Server Name</label>
                <input
                  type="text"
                  value={newServer.name}
                  onChange={(e) => setNewServer((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., filesystem, fetch"
                  className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg"
                />
              </div>

              <div>
                <label className="block text-sm text-claude-text-muted mb-1">Type</label>
                <div className="flex gap-2">
                  <button
                    className={`flex-1 px-3 py-2 text-sm rounded ${
                      newServer.type === "stdio"
                        ? "bg-claude-accent text-white"
                        : "bg-claude-surface text-claude-text-secondary"
                    }`}
                    onClick={() => setNewServer((prev) => ({ ...prev, type: "stdio" }))}
                  >
                    Stdio (Command)
                  </button>
                  <button
                    className={`flex-1 px-3 py-2 text-sm rounded ${
                      newServer.type === "http"
                        ? "bg-claude-accent text-white"
                        : "bg-claude-surface text-claude-text-secondary"
                    }`}
                    onClick={() => setNewServer((prev) => ({ ...prev, type: "http" }))}
                  >
                    HTTP (URL)
                  </button>
                </div>
              </div>

              {newServer.type === "stdio" ? (
                <>
                  <div>
                    <label className="block text-sm text-claude-text-muted mb-1">Command</label>
                    <input
                      type="text"
                      value={newServer.command}
                      onChange={(e) => setNewServer((prev) => ({ ...prev, command: e.target.value }))}
                      placeholder="e.g., npx, python"
                      className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-claude-text-muted mb-1">Arguments (space-separated)</label>
                    <input
                      type="text"
                      value={newServer.args}
                      onChange={(e) => setNewServer((prev) => ({ ...prev, args: e.target.value }))}
                      placeholder="-y @modelcontextprotocol/server-filesystem"
                      className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-claude-text-muted mb-1">Environment Variables (optional)</label>
                    <textarea
                      value={newServer.env}
                      onChange={(e) => setNewServer((prev) => ({ ...prev, env: e.target.value }))}
                      placeholder="KEY=value&#10;ANOTHER_KEY=another_value"
                      rows={3}
                      className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-claude-text-muted mb-1">Enabled Tools (optional)</label>
                    <input
                      type="text"
                      value={newServer.enabledTools}
                      onChange={(e) => setNewServer((prev) => ({ ...prev, enabledTools: e.target.value }))}
                      placeholder="Comma-separated. Leave empty for all tools. e.g. read_file, write_file"
                      className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-sm text-claude-text-muted mb-1">URL</label>
                    <input
                      type="text"
                      value={newServer.url}
                      onChange={(e) => setNewServer((prev) => ({ ...prev, url: e.target.value }))}
                      placeholder="https://api.example.com/mcp"
                      className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-claude-text-muted mb-1">Enabled Tools (optional)</label>
                    <input
                      type="text"
                      value={newServer.enabledTools}
                      onChange={(e) => setNewServer((prev) => ({ ...prev, enabledTools: e.target.value }))}
                      placeholder="Comma-separated. Leave empty for all tools"
                      className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg"
                    />
                  </div>
                </>
              )}
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <Button variant="ghost" onClick={() => setShowAddDialog(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleAdd}
                disabled={
                  !newServer.name ||
                  (newServer.type === "stdio" && !newServer.command) ||
                  (newServer.type === "http" && !newServer.url)
                }
              >
                Add Server
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
