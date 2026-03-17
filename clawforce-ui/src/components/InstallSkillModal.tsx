import { useState } from "react";
import Modal from "./Modal";
import { useClaws } from "../lib/queries";
import { api } from "../lib/api";
import type { MarketplaceSkill, AgentSummary } from "../lib/types";

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
  skill: MarketplaceSkill | null;
  onInstalled?: (agentId: string, slug: string) => void;
}

export default function InstallSkillModal({ open, onClose, skill, onInstalled }: Props) {
  const { data: agents = [], isLoading: agentsLoading } = useClaws();
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [envValues, setEnvValues] = useState<Record<string, string>>({});
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const runningAgents = agents.filter((a: AgentSummary) => a.status === "running");
  const requiredEnv = skill?.required_env ?? [];

  async function handleInstall() {
    if (!skill || !selectedAgentId) return;
    setInstalling(true);
    setError(null);
    try {
      const env = Object.keys(envValues).length > 0 ? envValues : undefined;
      await api.agents.installSkill(selectedAgentId, skill.slug, skill.version || undefined, env);
      setSuccess(true);
      onInstalled?.(selectedAgentId, skill.slug);
      setTimeout(() => {
        onClose();
        setSuccess(false);
        setSelectedAgentId("");
      }, 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Install failed");
    } finally {
      setInstalling(false);
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

  if (!skill) return null;

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Install Skill"
      icon={
        <svg className="h-4 w-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
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
              disabled={installing || !selectedAgentId}
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
          <p className="text-sm font-medium text-claude-text-primary">Skill installed!</p>
          <p className="text-xs text-claude-text-muted mt-1">
            {skill.name} is now available on your agent.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-lg border border-claude-border bg-claude-surface p-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 shrink-0">
                <svg className="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-claude-text-primary">{skill.name}</span>
                  {skill.version && (
                    <span className="rounded px-1.5 py-px text-[10px] font-mono text-claude-text-muted ring-1 ring-claude-border">
                      v{skill.version}
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-claude-text-muted line-clamp-2">{skill.description}</p>
              </div>
            </div>
          </div>

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
                No running agents. Start an agent first to install skills.
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
