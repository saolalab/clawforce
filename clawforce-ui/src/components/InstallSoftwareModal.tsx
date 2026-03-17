import { useState, useEffect } from "react";
import Modal from "./Modal";
import { useClaws, useInstallSoftware, useAgent } from "../lib/queries";
import type { SoftwareCatalogEntry, SoftwareInstallResult, AgentSummary } from "../lib/types";

const css = {
  btn: "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
  select:
    "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
  input:
    "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
};

function sanitizeSoftwareKey(s: string): string {
  return s.replace(/\//g, "_").replace(/\./g, "_").replace(/@/g, "_").replace(/^_+|_+$/g, "") || "software";
}

interface Props {
  open: boolean;
  onClose: () => void;
  entry: SoftwareCatalogEntry | null;
  agentId?: string;
}

export default function InstallSoftwareModal({ open, onClose, entry, agentId: preselectedAgentId }: Props) {
  const { data: agents = [], isLoading: agentsLoading } = useClaws();
  const [selectedAgentId, setSelectedAgentId] = useState<string>(preselectedAgentId ?? "");
  const [envValues, setEnvValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SoftwareInstallResult | null>(null);
  const [showLogs, setShowLogs] = useState(false);

  const installMutation = useInstallSoftware(selectedAgentId);
  const installing = installMutation.isPending;

  const runningAgents = agents.filter((a: AgentSummary) => a.status === "running");
  const requiredEnv = entry?.required_env ?? [];

  const { data: selectedAgent } = useAgent(selectedAgentId || undefined);

  const alreadyInstalled = (() => {
    if (!selectedAgent || !entry) return false;
    const sw = selectedAgent.tools?.software;
    if (!sw) return false;
    const key = sanitizeSoftwareKey(entry.id);
    return entry.id in sw || key in sw;
  })();

  const agentNotRunning = selectedAgent && selectedAgent.status !== "running";

  useEffect(() => {
    if (preselectedAgentId) {
      setSelectedAgentId(preselectedAgentId);
    }
  }, [preselectedAgentId]);

  useEffect(() => {
    setError(null);
  }, [selectedAgentId]);

  async function handleInstall() {
    if (!entry || !selectedAgentId) return;
    setError(null);
    setResult(null);
    setShowLogs(false);
    try {
      const res = await installMutation.mutateAsync({
        software_id: entry.id,
        env: Object.keys(envValues).length > 0 ? envValues : undefined,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Install failed");
    }
  }

  function handleClose() {
    if (!installing) {
      onClose();
      setError(null);
      setResult(null);
      setShowLogs(false);
      setSelectedAgentId(preselectedAgentId ?? "");
      setEnvValues({});
    }
  }

  if (!entry) return null;

  const succeeded = result?.ok === true;
  const failed = result != null && !result.ok;

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Install Software"
      icon={
        <svg className="h-4 w-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      }
      footer={
        succeeded ? (
          <button
            type="button"
            onClick={handleClose}
            className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover`}
          >
            Done
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={handleClose}
              disabled={installing}
              className={`${css.btn} text-claude-text-secondary hover:bg-claude-surface disabled:opacity-40`}
            >
              {failed ? "Close" : "Cancel"}
            </button>
            {!failed && (
              <button
                type="button"
                onClick={handleInstall}
                disabled={installing || !selectedAgentId || agentNotRunning}
                className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover disabled:opacity-40`}
              >
                {installing ? "Installing..." : "Install"}
              </button>
            )}
            {failed && (
              <button
                type="button"
                onClick={handleInstall}
                className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover`}
              >
                Retry
              </button>
            )}
          </>
        )
      }
    >
      {/* Success state */}
      {succeeded && (
        <div className="space-y-4">
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 mb-3">
              <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-sm font-medium text-claude-text-primary">Software installed!</p>
            <p className="text-xs text-claude-text-muted mt-1">
              {entry.name} is installed. Subagents can use it via software_exec.
              {Object.keys(envValues).some((k) => envValues[k]?.trim()) && " API keys saved."}
            </p>
          </div>

          {/* Verification status */}
          <div className="flex items-center gap-2 rounded-lg border border-claude-border bg-claude-surface px-3 py-2">
            {result.verified ? (
              <>
                <svg className="h-4 w-4 text-green-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-xs text-green-700">Command verified in PATH</span>
              </>
            ) : (
              <>
                <svg className="h-4 w-4 text-amber-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <span className="text-xs text-amber-700">Command not found in PATH (may need agent restart)</span>
              </>
            )}
          </div>

          {/* Logs toggle */}
          {result.logs && (
            <div>
              <button
                type="button"
                onClick={() => setShowLogs(!showLogs)}
                className="flex items-center gap-1.5 text-xs text-claude-text-muted hover:text-claude-text-secondary transition-colors"
              >
                <svg className={`h-3 w-3 transition-transform ${showLogs ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                Install logs (exit code: {result.exit_code})
              </button>
              {showLogs && (
                <pre className="mt-2 max-h-48 overflow-auto rounded-lg border border-claude-border bg-gray-900 p-3 text-[11px] leading-relaxed text-gray-200 font-mono whitespace-pre-wrap">
                  {result.logs}
                </pre>
              )}
            </div>
          )}
        </div>
      )}

      {/* Failed state */}
      {failed && (
        <div className="space-y-4">
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100 mb-3">
              <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="text-sm font-medium text-red-700">Installation failed</p>
            <p className="text-xs text-claude-text-muted mt-1">{result.message}</p>
          </div>

          {result.logs && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-claude-text-secondary">Install logs (exit code: {result.exit_code})</span>
              </div>
              <pre className="max-h-56 overflow-auto rounded-lg border border-red-200 bg-gray-900 p-3 text-[11px] leading-relaxed text-gray-200 font-mono whitespace-pre-wrap">
                {result.logs}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Initial / form state */}
      {!result && (
        <div className="space-y-4">
          {installing && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              <svg className="h-4 w-4 shrink-0 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Installation may take several minutes. Please do not close this window.
            </div>
          )}
          <div className="rounded-lg border border-claude-border bg-claude-surface p-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 shrink-0">
                <svg className="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="min-w-0">
                <span className="text-sm font-medium text-claude-text-primary">{entry.name}</span>
                {entry.author && (
                  <p className="text-[10px] text-claude-text-muted mt-0.5">by {entry.author}</p>
                )}
                <p className="mt-0.5 text-xs text-claude-text-muted line-clamp-2">{entry.description}</p>
              </div>
            </div>
          </div>

          {!preselectedAgentId && (
            <div>
              <label className="block text-xs font-medium text-claude-text-secondary mb-1.5">
                Install to Agent
              </label>
              {agentsLoading ? (
                <p className="text-xs text-claude-text-muted">Loading agents...</p>
              ) : runningAgents.length === 0 ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                  No running agents. Start an agent first to install software.
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
          )}

          {agentNotRunning && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
              <svg className="h-4 w-4 text-red-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span className="text-xs text-red-700">
                Agent is not running. Start the agent first to install software.
              </span>
            </div>
          )}

          {alreadyInstalled && !agentNotRunning && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <svg className="h-4 w-4 text-amber-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-xs text-amber-700">
                {entry.name} is already installed on this agent. Installing again will update/repair it.
              </span>
            </div>
          )}

          {requiredEnv.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-claude-text-secondary mb-1.5">
                API keys (saved with this software)
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
                      placeholder={`Enter ${key}`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

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
