import { useState } from "react";
import { Button } from "../ui";
import ModelSelect from "../ModelSelect";
import type { Agent } from "../../lib/types";

interface AgentConfigPanelProps {
  agent: Agent | undefined;
  onSave: (config: Partial<Agent>) => void;
  isSaving: boolean;
}

/**
 * AgentConfigPanel displays and allows editing of agent configuration.
 * Includes model selection, temperature, max_tokens, and objectives.
 */
export function AgentConfigPanel({
  agent,
  onSave,
  isSaving,
}: AgentConfigPanelProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [config, setConfig] = useState<Partial<Agent>>({});

  const handleEdit = () => {
    setConfig({
      name: agent?.name,
      description: agent?.description,
      model: agent?.model,
      temperature: agent?.temperature,
      max_tokens: agent?.max_tokens,
      max_tool_iterations: agent?.max_tool_iterations,
      memory_window: agent?.memory_window,
    });
    setIsEditing(true);
  };

  const handleSave = () => {
    onSave(config);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setConfig({});
    setIsEditing(false);
  };

  const updateField = <K extends keyof Agent>(field: K, value: Agent[K]) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  if (!agent) {
    return (
      <div className="p-4 bg-claude-surface rounded-lg">
        <p className="text-claude-text-secondary">Loading configuration...</p>
      </div>
    );
  }

  return (
    <div className="bg-claude-input rounded-xl border border-claude-border p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-claude-text-primary">Configuration</h3>
        {!isEditing ? (
          <Button variant="ghost" size="sm" onClick={handleEdit}>
            Edit
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={handleCancel}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleSave} disabled={isSaving}>
              {isSaving ? "Saving..." : "Save"}
            </Button>
          </div>
        )}
      </div>

      <div className="space-y-4">
        {/* Model Selection */}
        <div>
          <label className="block text-xs font-medium text-claude-text-muted mb-1">
            Model
          </label>
          {isEditing ? (
            <ModelSelect
              value={config.model || agent.model}
              onChange={(model) => updateField("model", model)}
            />
          ) : (
            <p className="text-sm text-claude-text-primary">{agent.model}</p>
          )}
        </div>

        {/* Temperature */}
        <div>
          <label className="block text-xs font-medium text-claude-text-muted mb-1">
            Temperature ({(isEditing ? config.temperature : agent.temperature) ?? 0.7})
          </label>
          {isEditing ? (
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={config.temperature ?? agent.temperature ?? 0.7}
              onChange={(e) => updateField("temperature", parseFloat(e.target.value))}
              className="w-full"
            />
          ) : (
            <p className="text-sm text-claude-text-primary">{agent.temperature ?? 0.7}</p>
          )}
        </div>

        {/* Max Tokens */}
        <div>
          <label className="block text-xs font-medium text-claude-text-muted mb-1">
            Max Tokens
          </label>
          {isEditing ? (
            <input
              type="number"
              value={config.max_tokens ?? agent.max_tokens ?? 4096}
              onChange={(e) => updateField("max_tokens", parseInt(e.target.value, 10))}
              className={css.input}
              min="1"
              max="128000"
            />
          ) : (
            <p className="text-sm text-claude-text-primary">{agent.max_tokens ?? 4096}</p>
          )}
        </div>

        {/* Max Tool Iterations */}
        <div>
          <label className="block text-xs font-medium text-claude-text-muted mb-1">
            Max Tool Iterations
          </label>
          {isEditing ? (
            <input
              type="number"
              value={config.max_tool_iterations ?? agent.max_tool_iterations ?? 10}
              onChange={(e) => updateField("max_tool_iterations", parseInt(e.target.value, 10))}
              className={css.input}
              min="1"
              max="100"
            />
          ) : (
            <p className="text-sm text-claude-text-primary">{agent.max_tool_iterations ?? 10}</p>
          )}
        </div>

        {/* Memory Window */}
        <div>
          <label className="block text-xs font-medium text-claude-text-muted mb-1">
            Memory Window (messages)
          </label>
          {isEditing ? (
            <input
              type="number"
              value={config.memory_window ?? agent.memory_window ?? 20}
              onChange={(e) => updateField("memory_window", parseInt(e.target.value, 10))}
              className={css.input}
              min="1"
              max="1000"
            />
          ) : (
            <p className="text-sm text-claude-text-primary">{agent.memory_window ?? 20}</p>
          )}
        </div>
      </div>
    </div>
  );
}

const css = {
  input: "w-full rounded-lg border border-claude-border bg-claude-bg px-3 py-1.5 text-sm text-claude-text-primary focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30",
};
