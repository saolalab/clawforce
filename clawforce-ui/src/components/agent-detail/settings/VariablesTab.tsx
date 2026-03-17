import { useEffect, useState } from "react";
import { useAgentVariables, useSaveVariables } from "../../../lib/queries";
import { css } from "../constants";
import { Section } from "../ui/Section";

type Entry = [string, string, boolean];

function toEntries(data: Record<string, string> | undefined): Entry[] {
  if (!data || Object.keys(data).length === 0) return [["", "", true]];
  return Object.entries(data).map(([k, v]) => [k, v, v.startsWith("***")]);
}

export function VariablesTab({ agentId }: { agentId: string }) {
  const { data: variablesData } = useAgentVariables(agentId);
  const saveMut = useSaveVariables(agentId);
  const [entries, setEntries] = useState<Entry[]>(() => toEntries(variablesData));
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setEntries(toEntries(variablesData));
  }, [variablesData]);

  function addRow() {
    setEntries((prev) => [...prev, ["", "", true]]);
  }

  function updateKey(idx: number, newKey: string) {
    setEntries((prev) =>
      prev.map((e, i) => (i === idx ? [newKey, e[1], e[2]] : e)) as Entry[]
    );
  }

  function updateValue(idx: number, newVal: string) {
    setEntries((prev) =>
      prev.map((e, i) => (i === idx ? [e[0], newVal, e[2]] : e)) as Entry[]
    );
  }

  function toggleSecret(idx: number) {
    setEntries((prev) =>
      prev.map((e, i) => (i === idx ? [e[0], e[1], !e[2]] : e)) as Entry[]
    );
  }

  function removeRow(idx: number) {
    setEntries((prev) => prev.filter((_, i) => i !== idx));
  }

  function save() {
    const variables: Record<string, string> = {};
    const secretKeys: string[] = [];
    for (const [k, v, secret] of entries) {
      const key = k.trim();
      if (!key) continue;
      if (v.startsWith("***")) continue;
      variables[key] = v;
      if (secret) secretKeys.push(key);
    }
    saveMut.mutate({ variables, secret_keys: secretKeys }, {
      onSuccess: () => setSaved(true),
    });
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="space-y-3">
      <Section title="Variables">
        <div className="mb-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600 flex items-start gap-2">
          <svg className="h-4 w-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Variable changes require an <strong>agent restart</strong> to take effect.</span>
        </div>
        <p className="text-sm text-claude-text-muted mb-2">
          Key-value pairs are injected as environment variables for this agent (process, MCP servers, and software tools).
          Secret values are redacted; non-secret values are visible.
        </p>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-claude-text-secondary">Environment variables</span>
          <button
            type="button"
            onClick={addRow}
            className="text-[10px] text-claude-accent hover:text-claude-accent-hover transition-colors font-medium"
          >
            + Add variable
          </button>
        </div>
        <div className="space-y-2">
          {entries.map(([key, value, secret], idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                className={`${css.input} flex-[2] font-mono text-xs`}
                value={key}
                onChange={(e) => updateKey(idx, e.target.value)}
                placeholder="KEY"
              />
              <input
                className={`${css.input} flex-[3] text-xs`}
                type={secret ? "password" : "text"}
                value={value}
                onChange={(e) => updateValue(idx, e.target.value)}
                placeholder="value"
              />
              <label className="flex items-center gap-1 shrink-0 text-xs text-claude-text-muted cursor-pointer">
                <input
                  type="checkbox"
                  checked={secret}
                  onChange={() => toggleSecret(idx)}
                  className="rounded border-gray-300"
                />
                Secret
              </label>
              <button
                type="button"
                onClick={() => removeRow(idx)}
                className="text-red-400 hover:text-red-600 transition-colors shrink-0 p-1"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={save}
            disabled={saveMut.isPending}
            className={`${css.btn} ${saved ? "bg-green-50 text-green-700 ring-1 ring-green-200" : "bg-claude-accent text-white hover:bg-claude-accent-hover"} disabled:opacity-40 text-xs px-3 py-1.5`}
          >
            {saveMut.isPending ? "Saving…" : saved ? "Saved" : "Save variables"}
          </button>
        </div>
      </Section>
    </div>
  );
}
