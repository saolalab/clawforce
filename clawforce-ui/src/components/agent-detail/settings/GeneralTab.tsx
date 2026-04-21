import { useEffect, useRef, useState } from "react";
import { api } from "../../../lib/api";
import { ClawIcon } from "../../ClawIcon";
import { css, HEARTBEAT_SCHEDULE_OPTIONS, PRESET_ROWS, SECURITY_PRESETS } from "../constants";
import { detectProvider, fmtPresetValue, heartbeatScheduleToOption } from "../utils";
import { Section, Toggle } from "../ui/Section";
import { ModelProviderSection } from "./ModelProviderSection";
import { SecurityPresetCard } from "./SecurityPresetCard";
import type { Agent } from "../types";

type DockerLevel = "permissive" | "sandboxed" | "privileged";

function DockerSettings({
  agent,
  update,
  updateTools,
  dockerPresets,
}: {
  agent: Agent;
  update: (p: Record<string, unknown>) => void;
  updateTools: (p: Record<string, unknown>) => void;
  dockerPresets: { permissive: Record<string, unknown>; sandboxed: Record<string, unknown>; privileged?: Record<string, unknown> } | null;
}) {
  const [showDetails, setShowDetails] = useState(false);
  const currentLevel = (agent.security?.docker?.level || "privileged") as DockerLevel;
  const activePreset =
    dockerPresets && currentLevel in dockerPresets
      ? dockerPresets[currentLevel as keyof typeof dockerPresets]
      : dockerPresets?.permissive;

  const setLevel = (level: DockerLevel) => {
    update({
      security: {
        ...agent.security,
        docker: { ...agent.security?.docker, level },
      },
    });
  };

  return (
    <div>
      <div className="grid grid-cols-1 min-[480px]:grid-cols-2 min-[720px]:grid-cols-3 gap-1.5 mb-1.5">
        <SecurityPresetCard
          preset={SECURITY_PRESETS.permissive}
          isSelected={currentLevel === "permissive"}
          onClick={() => setLevel("permissive")}
        />
        <SecurityPresetCard
          preset={SECURITY_PRESETS.sandboxed}
          isSelected={currentLevel === "sandboxed"}
          onClick={() => setLevel("sandboxed")}
        />
        <SecurityPresetCard
          preset={SECURITY_PRESETS.privileged}
          isSelected={currentLevel === "privileged"}
          onClick={() => setLevel("privileged")}
        />
      </div>

      {dockerPresets && activePreset && (
        <div className="mt-1.5">
          <button
            type="button"
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center gap-1.5 text-[11px] text-claude-text-muted hover:text-claude-text-secondary transition-colors"
          >
            <svg className={`h-3 w-3 transition-transform ${showDetails ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Technical details
          </button>
          {showDetails && (
            <div className="mt-1 rounded-md border border-claude-border bg-claude-bg px-2.5 py-1.5 space-y-1.5">
              <dl className="space-y-1 text-[10px]">
                {PRESET_ROWS.map(([key, label]) => (
                  <div key={key} className="flex justify-between gap-4">
                    <dt className="text-claude-text-muted shrink-0">{label}</dt>
                    <dd className="truncate text-right font-mono text-claude-text-secondary" title={fmtPresetValue(activePreset[key])}>
                      {fmtPresetValue(activePreset[key])}
                    </dd>
                  </div>
                ))}
              </dl>
              <div className="border-t border-claude-border pt-2">
                <label className={css.label}>Shell Timeout (s)</label>
                <input
                  type="number"
                  className={css.input}
                  value={agent.tools.exec?.timeout ?? 60}
                  onChange={(e) => updateTools({ exec: { ...agent.tools.exec, timeout: parseInt(e.target.value) || 60 } })}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function GeneralTab({ agentId, agent, update, updateTools }: { agentId: string; agent: Agent; update: (p: Partial<Agent>) => void; updateTools: (p: Record<string, unknown>) => void }) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showLLM, setShowLLM] = useState(true);
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [runtimeType, setRuntimeType] = useState<"process" | "docker">("process");
  const [dockerPresets, setDockerPresets] = useState<{
    permissive: Record<string, unknown>;
    sandboxed: Record<string, unknown>;
    privileged?: Record<string, unknown>;
  } | null>(null);
  const colorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.runtime.info().then((info) => {
      setRuntimeType(info.runtime_type as "process" | "docker");
      if (info.docker_presets) setDockerPresets(info.docker_presets);
    });
  }, []);

  useEffect(() => {
    if (!showColorPicker) return;
    function handleClick(e: MouseEvent) {
      if (colorRef.current && !colorRef.current.contains(e.target as Node)) setShowColorPicker(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showColorPicker]);

  return (
    <div className="space-y-3">
      <Section title="Agent">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={css.label}>Name</label>
            <div className="flex items-center gap-2">
              <div className="relative" ref={colorRef}>
                <button type="button" onClick={() => setShowColorPicker((v) => !v)} className="shrink-0 rounded-lg p-0.5 hover:bg-claude-surface transition-colors" title="Change color">
                  <ClawIcon className="h-6 w-6" color={agent.color || undefined} />
                </button>
                {showColorPicker && (
                  <div className="absolute left-0 top-full z-20 mt-1.5 w-56 rounded-xl border border-claude-border bg-white p-3 shadow-lg">
                    <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-claude-text-muted">Pick a color</p>
                    <div className="grid grid-cols-8 gap-1.5">
                      {[
                        "#ef4444", "#f97316", "#f59e0b", "#eab308", "#84cc16", "#22c55e", "#10b981", "#14b8a6",
                        "#06b6d4", "#0ea5e9", "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
                      ].map((c) => (
                        <button
                          key={c}
                          type="button"
                          onClick={() => { update({ color: c }); setShowColorPicker(false); }}
                          className={`h-5 w-5 rounded-full border-2 transition-all hover:scale-125 ${agent.color === c ? "border-claude-text-primary ring-1 ring-claude-text-primary/30 scale-110" : "border-transparent"}`}
                          style={{ backgroundColor: c }}
                        />
                      ))}
                    </div>
                    <div className="mt-2.5 flex items-center justify-between border-t border-claude-border pt-2">
                      <label className="flex cursor-pointer items-center gap-2 text-xs text-claude-text-muted hover:text-claude-text-secondary">
                        Custom
                        <input
                          type="color"
                          value={agent.color || "#ef4444"}
                          onChange={(e) => update({ color: e.target.value })}
                          className="h-5 w-5 cursor-pointer rounded border-0 p-0"
                        />
                      </label>
                      {agent.color && (
                        <button type="button" onClick={() => { update({ color: "" }); setShowColorPicker(false); }} className="text-xs text-claude-text-muted hover:text-claude-text-secondary">
                          Reset
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
              <input className={`${css.input} flex-1`} value={agent.name} onChange={(e) => update({ name: e.target.value })} />
            </div>
          </div>
          <div>
            <label className={css.label}>Agent Status</label>
            <select
              className={css.input}
              value={agent.enabled ? "available" : "resting"}
              onChange={(e) => update({ enabled: e.target.value === "available" })}
            >
              <option value="available">Available to work</option>
              <option value="resting">Taking a rest</option>
            </select>
          </div>
          <div className="col-span-2">
            <label className={css.label}>Description</label>
            <textarea
              className={`${css.input} resize-none`}
              rows={2}
              value={agent.description}
              onChange={(e) => update({ description: e.target.value })}
              placeholder="What does this agent do?"
            />
          </div>
        </div>

        <div className="mt-3 border-t border-claude-border pt-2.5">
          <button
            type="button"
            onClick={() => setShowLLM(!showLLM)}
            className="flex w-full items-center justify-between gap-2 text-left text-xs font-medium text-claude-text-muted hover:text-claude-text-secondary transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <svg
                className={`h-3 w-3 transition-transform ${showLLM ? "rotate-90" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              LLM Provider & Model
            </span>
            {!showLLM && agent.model && (
              <span className="truncate text-claude-text-secondary font-normal">
                {(() => {
                  const p = detectProvider(agent.model);
                  const modelDisplay = agent.model?.includes("/") ? agent.model.split("/").pop() : agent.model;
                  return p ? `${p.label} / ${modelDisplay}` : modelDisplay;
                })()}
              </span>
            )}
          </button>
          {showLLM && (
            <div className="mt-2.5">
              <ModelProviderSection
                agentId={agentId}
                model={agent.model}
                savedProviders={agent.providers as Record<string, Record<string, unknown>> | undefined}
                onModelChange={(v) => update({ model: v })}
                onProviderChange={(provider, patch) => {
                  update({
                    providers: {
                      ...agent.providers,
                      [provider]: { ...(agent.providers?.[provider] || {}), ...patch },
                    },
                  });
                }}
              />
            </div>
          )}
        </div>

        <div className="mt-3 border-t border-claude-border pt-2.5">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1.5 text-xs font-medium text-claude-text-muted hover:text-claude-text-secondary transition-colors"
          >
            <svg
              className={`h-3 w-3 transition-transform ${showAdvanced ? "rotate-90" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Advanced Settings
          </button>

          {showAdvanced && (
            <div className="mt-2.5 grid grid-cols-2 gap-3">
              <div>
                <label className={css.label}>
                  Temperature <span className="font-mono text-claude-accent">{agent.temperature}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={agent.temperature}
                  onChange={(e) => update({ temperature: parseFloat(e.target.value) })}
                  className="w-full accent-claude-accent mt-0.5"
                />
              </div>
              <div>
                <label className={css.label}>Max Tokens</label>
                <input
                  type="number"
                  className={css.input}
                  value={agent.max_tokens}
                  onChange={(e) => update({ max_tokens: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div>
                <label className={css.label}>Max Tool Iterations</label>
                <input
                  type="number"
                  className={css.input}
                  value={agent.max_tool_iterations}
                  onChange={(e) => update({ max_tool_iterations: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div>
                <label className={css.label}>Memory Window</label>
                <input
                  type="number"
                  className={css.input}
                  value={agent.memory_window}
                  onChange={(e) => update({ memory_window: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div>
                <label className={css.label}>Shell Timeout (s)</label>
                <input
                  type="number"
                  className={css.input}
                  value={agent.tools.exec?.timeout ?? 60}
                  onChange={(e) => updateTools({ exec: { ...agent.tools.exec, timeout: parseInt(e.target.value) || 60 } })}
                />
              </div>
              <div className="col-span-2 border-t border-claude-border pt-2 mt-1">
                <p className={css.label}>Fault tolerance (LLM retries)</p>
                <div className="grid grid-cols-2 gap-3 mt-1">
                  <div>
                    <label className="text-xs text-claude-text-muted">Max retry attempts</label>
                    <input
                      type="number"
                      className={css.input}
                      value={agent.fault_tolerance?.max_attempts ?? 3}
                      onChange={(e) => update({ fault_tolerance: { max_attempts: parseInt(e.target.value) || 3, backoff_factor: agent.fault_tolerance?.backoff_factor ?? 1 } })}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-claude-text-muted">Backoff factor (seconds)</label>
                    <input
                      type="number"
                      className={css.input}
                      step="0.5"
                      value={agent.fault_tolerance?.backoff_factor ?? 1}
                      onChange={(e) => update({ fault_tolerance: { max_attempts: agent.fault_tolerance?.max_attempts ?? 3, backoff_factor: parseFloat(e.target.value) || 1 } })}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </Section>

      <Section title="Security">
        <div className="space-y-3">
          <div>
            <Toggle
              checked={agent.tools?.exec?.policy?.relaxed ?? true}
              onChange={(v) =>
                updateTools({
                  exec: {
                    ...agent.tools.exec,
                    policy: {
                      ...agent.tools.exec?.policy,
                      mode: agent.tools.exec?.policy?.mode ?? "allow_all",
                      allow: agent.tools.exec?.policy?.allow ?? [],
                      deny: agent.tools.exec?.policy?.deny ?? [],
                      relaxed: v,
                    },
                  },
                })
              }
              label="Relax Shell Policy"
            />
            <p className="text-[11px] text-claude-text-muted mt-1">
              When enabled, allows pipes, redirects, and other shell operators that are normally blocked.
            </p>
          </div>
          {runtimeType === "docker" && (
            <DockerSettings agent={agent} update={update} updateTools={updateTools} dockerPresets={dockerPresets} />
          )}
        </div>
      </Section>

      <Section title="Heartbeat">
        <p className="text-[11px] text-claude-text-muted mb-3">
          How often the agent checks <code className="bg-claude-surface px-1 rounded text-[10px]">HEARTBEAT.md</code> in the workspace for tasks.
        </p>
        <div className="space-y-3">
          <Toggle
            checked={agent.heartbeat?.enabled ?? true}
            onChange={(v) => update({ heartbeat: { ...agent.heartbeat, enabled: v, interval_s: agent.heartbeat?.interval_s ?? 1800, cron_expr: agent.heartbeat?.cron_expr ?? "", timezone: agent.heartbeat?.timezone ?? "" } })}
            label="Enable heartbeat"
          />
          <div>
            <label className={css.label}>Schedule</label>
            <select
              className={css.input}
              value={heartbeatScheduleToOption(agent.heartbeat?.interval_s ?? 1800)}
              onChange={(e) => {
                const interval_s = Number(e.target.value);
                update({ heartbeat: { ...agent.heartbeat, enabled: agent.heartbeat?.enabled ?? true, interval_s, cron_expr: agent.heartbeat?.cron_expr ?? "", timezone: agent.heartbeat?.timezone ?? "" } });
              }}
              disabled={!agent.heartbeat?.enabled}
            >
              {HEARTBEAT_SCHEDULE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Section>
    </div>
  );
}
