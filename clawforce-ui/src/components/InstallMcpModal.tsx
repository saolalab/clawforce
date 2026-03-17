import { useState } from "react";
import Modal from "./Modal";
import { useClaws, useInstallMcpServer } from "../lib/queries";
import type { MCPRegistryServer, AgentSummary } from "../lib/types";

const css = {
  btn: "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
  select:
    "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
  input:
    "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
};

interface Props {
  open: boolean;
  onClose: () => void;
  server: MCPRegistryServer | null;
  onInstalled?: (agentId: string, serverId: string) => void;
}

export default function InstallMcpModal({ open, onClose, server, onInstalled }: Props) {
  const { data: agents = [], isLoading: agentsLoading } = useClaws();
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [envValues, setEnvValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const installMutation = useInstallMcpServer(selectedAgentId);
  const installing = installMutation.isPending;

  const runningAgents = agents.filter((a: AgentSummary) => a.status === "running");
  const requiredEnv = server?.required_env ?? [];

  const getInstallConfig = (): { command?: string; args?: string[]; url?: string } | null => {
    if (!server) return null;
    const installCfg = server.install_config as Record<string, unknown> | Array<Record<string, unknown>>;
    if (Array.isArray(installCfg) && installCfg.length > 0) {
      const pkg = installCfg[0] as Record<string, unknown>;
      const transport = (pkg.transport || {}) as Record<string, unknown>;
      if (transport.type === "stdio" || pkg.registryType) {
        const identifier = String(pkg.identifier || "");
        if (pkg.registryType === "npm" || identifier.startsWith("@") || identifier.includes("/")) {
          return { command: "npx", args: ["-y", identifier] };
        }
      }
      if (transport.type === "streamable-http" || pkg.url) {
        return { url: String(pkg.url || transport.url || "") };
      }
    }
    if (typeof installCfg === "object" && !Array.isArray(installCfg) && installCfg !== null) {
      if (installCfg.url) return { url: String(installCfg.url) };
      if (installCfg.command) return { command: String(installCfg.command), args: (installCfg.args as string[]) || [] };
    }
    return null;
  };

  const installConfig = getInstallConfig();

  async function handleInstall() {
    if (!server || !selectedAgentId || !installConfig) return;
    setError(null);
    try {
      const env = Object.keys(envValues).length > 0 ? envValues : undefined;
      await installMutation.mutateAsync({
        server_id: server.id || server.slug,
        server_name: server.name || server.id,
        command: installConfig.command,
        args: installConfig.args,
        url: installConfig.url,
        env,
      });
      setSuccess(true);
      onInstalled?.(selectedAgentId, server.id || server.slug);
      setTimeout(() => {
        onClose();
        setSuccess(false);
        setSelectedAgentId("");
      }, 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Install failed");
    }
  }

  function handleClose() {
    if (!installing) {
      onClose();
      setError(null);
      setSuccess(false);
      setSelectedAgentId("");
      setEnvValues({});
    }
  }

  if (!server) return null;

  const isVerified = server.verified || server.is_verified;

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Install MCP Server"
      icon={
        <svg className="h-4 w-4 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
        </svg>
      }
      footer={
        success ? null : (
          <>
            <button
              type="button"
              onClick={handleClose}
              disabled={installing}
              className={`${css.btn} text-claude-text-secondary hover:bg-claude-surface disabled:opacity-40`}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleInstall}
              disabled={installing || !selectedAgentId || !installConfig}
              className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover disabled:opacity-40`}
            >
              {installing ? "Installing..." : "Install"}
            </button>
          </>
        )
      }
    >
      {success ? (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 mb-3">
            <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="text-sm font-medium text-claude-text-primary">MCP Server installed!</p>
          <p className="text-xs text-claude-text-muted mt-1">
            {server.name} is now available on your agent.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-lg border border-claude-border bg-claude-surface p-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/20 to-indigo-500/20 shrink-0">
                <svg className="h-5 w-5 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-claude-text-primary">{server.name}</span>
                  {server.version && (
                    <span className="rounded px-1.5 py-px text-[10px] font-mono text-claude-text-muted ring-1 ring-claude-border">
                      v{server.version}
                    </span>
                  )}
                  {isVerified && (
                    <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-px text-[10px] font-medium bg-blue-50 text-blue-700 ring-1 ring-blue-200">
                      <svg className="h-2.5 w-2.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Verified
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-claude-text-muted line-clamp-2">{server.description}</p>
              </div>
            </div>
          </div>

          {!installConfig && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              This server doesn't have an install configuration. Please refer to the documentation for manual setup.
            </div>
          )}

          {requiredEnv.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-claude-text-secondary mb-1.5">
                Environment variables (e.g. API keys)
              </label>
              <div className="space-y-2">
                {requiredEnv.map((key) => (
                  <div key={key}>
                    <label className="block text-[10px] text-claude-text-muted mb-0.5">{key}</label>
                    <input
                      type="password"
                      className={css.input}
                      value={envValues[key] ?? ""}
                      onChange={(e) => setEnvValues((prev) => ({ ...prev, [key]: e.target.value }))}
                      placeholder={`${key} (optional)`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-claude-text-secondary mb-1.5">
              Install to Agent
            </label>
            {agentsLoading ? (
              <p className="text-xs text-claude-text-muted">Loading agents...</p>
            ) : runningAgents.length === 0 ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                No running agents. Start an agent first to install MCP servers.
              </div>
            ) : (
              <select
                value={selectedAgentId}
                onChange={(e) => setSelectedAgentId(e.target.value)}
                className={css.select}
              >
                <option value="">Select an agent...</option>
                {runningAgents.map((agent: AgentSummary) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name || agent.id}
                  </option>
                ))}
              </select>
            )}
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {error}
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
