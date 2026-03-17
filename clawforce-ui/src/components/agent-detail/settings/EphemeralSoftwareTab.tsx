import { useEffect, useState } from "react";
import { useUninstallSoftware, useSaveConfig, useSoftwareCatalog } from "../../../lib/queries";
import { api } from "../../../lib/api";
import { css } from "../constants";
import { Section } from "../ui/Section";
import type { Agent, SoftwareInstalledEntry, ToolsCfg } from "../types";

export function EphemeralSoftwareTab({ agent, setTools }: { agent: Agent; setTools: (t: ToolsCfg) => void }) {
  const [isDockerRuntime, setIsDockerRuntime] = useState(false);
  const software = agent.tools?.software ?? {};
  const entries = Object.entries(software);
  const uninstallMutation = useUninstallSoftware(agent.id);
  const saveMut = useSaveConfig(agent.id);
  const { data: catalog = [] } = useSoftwareCatalog();
  const [uninstallingId, setUninstallingId] = useState<string | null>(null);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [envDraft, setEnvDraft] = useState<Record<string, string>>({});
  const warnings = agent.software_warnings ?? [];
  const softwareInstalling = agent.software_installing ?? false;

  function openEnvEditor(key: string, entry: SoftwareInstalledEntry) {
    const catalogEntry = catalog.find((c: { id: string; required_env?: string[] }) => {
      const sanitized = c.id.replace(/\//g, "_").replace(/\./g, "_").replace(/@/g, "_").replace(/^_+|_+$/g, "");
      return c.id === key || sanitized === key;
    });
    const knownKeys = catalogEntry?.required_env ?? [];
    const existingKeys = Object.keys(entry.env || {});
    const allKeys = [...new Set([...knownKeys, ...existingKeys])];

    const draft: Record<string, string> = {};
    for (const k of allKeys) {
      draft[k] = (entry.env || {})[k] ?? "";
    }
    if (allKeys.length === 0) draft[""] = "";
    setEnvDraft(draft);
    setEditingKey(key);
  }

  function saveEnv(key: string) {
    const cleaned: Record<string, string> = {};
    for (const [k, v] of Object.entries(envDraft)) {
      const trimmedKey = k.trim();
      if (trimmedKey) cleaned[trimmedKey] = v;
    }
    const patch = { tools: { software: { [key]: { ...software[key], env: cleaned } } } };
    saveMut.mutate(patch as unknown, { onSuccess: () => setEditingKey(null) });
  }

  function addEnvRow() {
    setEnvDraft((prev) => {
      let placeholder = "";
      while (placeholder in prev) placeholder += " ";
      return { ...prev, [placeholder]: "" };
    });
  }

  function updateEnvKey(oldKey: string, newKey: string) {
    setEnvDraft((prev) => {
      const next: Record<string, string> = {};
      for (const [k, v] of Object.entries(prev)) {
        next[k === oldKey ? newKey : k] = v;
      }
      return next;
    });
  }

  function updateEnvValue(key: string, value: string) {
    setEnvDraft((prev) => ({ ...prev, [key]: value }));
  }

  function removeEnvRow(key: string) {
    setEnvDraft((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }

  async function handleUninstall(entryId: string) {
    setUninstallingId(entryId);
    try {
      await uninstallMutation.mutateAsync(entryId);
      const updatedSoftware = { ...software };
      delete updatedSoftware[entryId];
      setTools({ ...agent.tools, software: updatedSoftware } as ToolsCfg);
    } finally {
      setUninstallingId(null);
    }
  }

  useEffect(() => {
    api.runtime.info().then((info) => setIsDockerRuntime(info.runtime_type === "docker"));
  }, []);

  if (!isDockerRuntime) {
    return (
      <Section title="Installed Software">
        <p className="text-sm text-claude-text-muted">
          Software installation is only available with Docker runtime backend.
        </p>
      </Section>
    );
  }

  return (
    <div className="space-y-4">
      <Section title="Installed Software">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm text-claude-text-muted">
            Subagents can run installed software via the software_exec tool.
          </p>
          <a
            href="/marketplace#software"
            className="text-sm text-claude-accent hover:underline font-medium inline-flex items-center gap-1"
          >
            Browse Software in Marketplace
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </a>
        </div>

        {softwareInstalling && (
          <div className="mb-3 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">
            <span className="font-medium">Reinstalling software</span>
            <span className="mx-1">—</span>
            {warnings.length > 0
              ? warnings.length === 1
                ? <><strong>{warnings[0].name}</strong> was not found after container restart. Restoring automatically…</>
                : <>{warnings.map(w => w.name).join(", ")} were not found after container restart. Restoring automatically…</>
              : "Restoring installed software after container restart…"}
          </div>
        )}
        {!softwareInstalling && warnings.length > 0 && (
          <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            <span className="font-medium">Software unavailable</span>
            <span className="mx-1">—</span>
            {warnings.length === 1
              ? <><strong>{warnings[0].name}</strong> was not found after container restart. Try reinstalling from the Marketplace.</>
              : <>{warnings.map(w => w.name).join(", ")} were not found after container restart. Try reinstalling from the Marketplace.</>
            }
          </div>
        )}

        {entries.length > 0 ? (
          <div className="space-y-2">
            {entries.map(([key, entry]: [string, SoftwareInstalledEntry]) => {
              const isEditing = editingKey === key;
              const envEntries = Object.entries(envDraft);
              const hasEnv = Object.keys(entry.env || {}).length > 0;

              return (
                <div key={key} className="rounded-lg border border-claude-border bg-claude-bg p-2.5">
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-claude-text-primary">{entry.name || key}</span>
                        <span className="rounded px-1.5 py-px text-[10px] font-medium bg-amber-50 text-amber-700 ring-1 ring-amber-200">
                          {entry.installed_via || "npm"}
                        </span>
                        {entry.verified === true && (
                          <span className="rounded px-1.5 py-px text-[10px] font-medium bg-green-50 text-green-700 ring-1 ring-green-200">verified</span>
                        )}
                        {entry.verified === false && (
                          <span className="rounded px-1.5 py-px text-[10px] font-medium bg-amber-50 text-amber-600 ring-1 ring-amber-200">unverified</span>
                        )}
                        {hasEnv && !isEditing && (
                          <span className="rounded px-1.5 py-px text-[10px] font-medium bg-blue-50 text-blue-600 ring-1 ring-blue-200">
                            {Object.keys(entry.env).length} secret{Object.keys(entry.env).length !== 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                      {entry.description && (
                        <p className="mt-0.5 text-xs text-claude-text-muted line-clamp-2">{entry.description}</p>
                      )}
                      <p className="mt-0.5 truncate text-xs text-claude-text-muted font-mono">
                        {entry.command} {(entry.args || []).join(" ")}
                      </p>
                      {entry.installed_at && (
                        <p className="mt-0.5 text-[10px] text-claude-text-muted">
                          Installed {new Date(entry.installed_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-3 shrink-0">
                      <button
                        onClick={() => isEditing ? setEditingKey(null) : openEnvEditor(key, entry)}
                        className="text-xs text-claude-text-muted hover:text-claude-accent transition-colors"
                      >
                        {isEditing ? "Cancel" : "Secrets"}
                      </button>
                      <button
                        onClick={() => handleUninstall(key)}
                        disabled={uninstallingId === key}
                        className="text-xs text-red-400 hover:text-red-600 transition-colors disabled:opacity-50"
                      >
                        {uninstallingId === key ? "Removing..." : "Uninstall"}
                      </button>
                    </div>
                  </div>

                  {isEditing && (
                    <div className="mt-2.5 pt-2.5 border-t border-claude-border space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-claude-text-secondary">Secrets</span>
                        <button
                          onClick={addEnvRow}
                          className="text-[10px] text-claude-accent hover:text-claude-accent-hover transition-colors font-medium"
                        >
                          + Add variable
                        </button>
                      </div>
                      {envEntries.length === 0 && (
                        <p className="text-xs text-claude-text-muted">No secrets. Add keys (e.g. GH_TOKEN).</p>
                      )}
                      {envEntries.map(([envKey, envVal], idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <input
                            className={`${css.input} flex-[2] font-mono text-xs`}
                            value={envKey}
                            onChange={(e) => updateEnvKey(envKey, e.target.value)}
                            placeholder="KEY"
                          />
                          <input
                            className={`${css.input} flex-[3] text-xs`}
                            type="password"
                            value={envVal}
                            onChange={(e) => updateEnvValue(envKey, e.target.value)}
                            placeholder="value"
                          />
                          <button
                            onClick={() => removeEnvRow(envKey)}
                            className="text-red-400 hover:text-red-600 transition-colors shrink-0 p-1"
                          >
                            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ))}
                      <div className="flex justify-end pt-1">
                        <button
                          onClick={() => saveEnv(key)}
                          disabled={saveMut.isPending}
                          className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover disabled:opacity-40 text-xs px-3 py-1`}
                        >
                          {saveMut.isPending ? "Saving..." : "Save Secrets"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-claude-text-muted">
            <svg className="h-8 w-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
            </svg>
            <p className="text-sm">No software installed yet.</p>
            <a
              href="/marketplace#software"
              className="mt-2 text-sm text-claude-accent hover:underline"
            >
              Browse Software in Marketplace
            </a>
          </div>
        )}
      </Section>
    </div>
  );
}
