import { useState } from "react";
import { useDeleteAgent } from "../../../lib/queries";
import { Button, TrashIcon } from "../../ui";
import ConfirmDialog from "../../ConfirmDialog";
import type { Agent, SettingsTab, ToolsCfg } from "../types";
import { GeneralTab } from "./GeneralTab";
import { VariablesTab } from "./VariablesTab";
import { ChannelsTab } from "./ChannelsTab";
import { ToolsTab } from "./ToolsTab";
import { SkillsTab } from "./SkillsTab";
import { EphemeralSoftwareTab } from "./EphemeralSoftwareTab";

export function SettingsContent({
  agentId,
  agent,
  update,
  updateTools,
  setTools,
  updateSkills,
  updateChannel,
  onSave,
  onDeleted,
  dirty,
  saving,
  saved,
  isOffline,
  restartRequired = false,
}: {
  agentId: string;
  agent: Agent;
  update: (p: Partial<Agent>) => void;
  updateTools: (p: Record<string, unknown>) => void;
  setTools: (t: ToolsCfg) => void;
  updateSkills: (disabled: string[]) => void;
  updateChannel: (ch: string, patch: Record<string, unknown>) => void;
  onSave: () => void;
  onDeleted: () => void;
  dirty: boolean;
  saving: boolean;
  saved: boolean;
  isOffline: boolean;
  restartRequired?: boolean;
}) {
  const [tab, setTab] = useState<SettingsTab>("general");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const deleteAgent = useDeleteAgent();

  const tabs: { key: SettingsTab; label: string }[] = [
    { key: "general", label: "General" },
    { key: "channels", label: "Channels" },
    { key: "tools", label: "Tools & MCP" },
    { key: "skills", label: "Skills" },
    { key: "software", label: "Software" },
    { key: "variables", label: "Variables" },
  ];

  async function handleConfirmDelete() {
    await deleteAgent.mutateAsync(agentId);
    onDeleted();
  }

  return (
    <div className="flex gap-6">
      <nav className="w-44 shrink-0">
        <div className="flex flex-col gap-1">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`group relative rounded-md px-3 py-2 text-left text-sm font-medium transition-all ${tab === t.key
                  ? "bg-claude-accent/10 text-claude-accent"
                  : "text-claude-text-secondary hover:bg-claude-surface hover:text-claude-text-primary"
                }`}
            >
              <span
                className={`absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full transition-all ${tab === t.key ? "bg-claude-accent" : "bg-transparent group-hover:bg-claude-border"
                  }`}
              />
              {t.label}
            </button>
          ))}
        </div>
      </nav>
      <div className="min-w-0 flex-1">
        {isOffline && dirty && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            <strong>Agent is offline.</strong> You can save now; changes will take effect when you start the agent.
          </div>
        )}
        <div className="mb-5 flex items-center justify-between gap-4 border-b border-claude-border/40 pb-4">
          <h2 className="text-base font-semibold text-claude-text-primary">
            {tabs.find((t) => t.key === tab)?.label}
          </h2>
          <div className="flex items-center gap-3 shrink-0">
            {restartRequired && (
              <span className="text-xs text-amber-700 font-medium">
                Restart required after change
              </span>
            )}
            <button
              onClick={onSave}
              disabled={!dirty || saving}
              title={saving ? "Saving…" : dirty ? "Save changes" : undefined}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${saved
                  ? "bg-green-50 text-green-700 ring-1 ring-green-200"
                  : dirty
                    ? "bg-claude-accent text-white shadow-sm hover:bg-claude-accent-hover"
                    : "bg-claude-surface text-claude-text-muted cursor-not-allowed ring-1 ring-claude-border"
                }`}
            >
              {saving ? "Saving…" : saved ? "✓ Saved" : "Save Changes"}
            </button>
          </div>
        </div>

        {tab === "general" && <GeneralTab agentId={agentId} agent={agent} update={update} updateTools={updateTools} />}
        {tab === "variables" && <VariablesTab agentId={agentId} />}
        {tab === "channels" && <ChannelsTab agent={agent} updateChannel={updateChannel} />}
        {tab === "tools" && <ToolsTab agentId={agentId} agent={agent} updateTools={updateTools} setTools={setTools} />}
        {tab === "skills" && <SkillsTab agentId={agentId} agent={agent} updateSkills={updateSkills} />}
        {tab === "software" && <EphemeralSoftwareTab agent={agent} setTools={setTools} />}

        {tab === "general" && (
          <div className="mt-6 rounded-lg border border-red-200 bg-red-50/50 p-3">
            <h3 className="text-sm font-medium text-red-800">Danger Zone</h3>
            <p className="mt-0.5 text-xs text-red-600">
              Permanently delete this agent and all its workspace files. This cannot be undone.
            </p>
            <Button variant="danger" size="sm" className="mt-2" onClick={() => setDeleteDialogOpen(true)}>
              <TrashIcon className="mr-1.5 h-3.5 w-3.5" />
              Delete Agent
            </Button>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleConfirmDelete}
        title="Delete Agent"
        message={`Are you sure you want to delete "${agent.name}"? This will remove all workspace files and configuration. This action cannot be undone.`}
        confirmLabel="Delete Agent"
        isPending={deleteAgent.isPending}
        variant="danger"
      />
    </div>
  );
}
