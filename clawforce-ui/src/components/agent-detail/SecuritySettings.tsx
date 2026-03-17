import { useState } from "react";
import { Button } from "../ui";
import type { ToolsConfig, ShellPolicyConfig, SecurityConfig } from "../../lib/types";

interface SecuritySettingsProps {
  tools: ToolsConfig | undefined;
  security: SecurityConfig | undefined;
  onSave: (config: { tools: ToolsConfig; security: SecurityConfig }) => void;
  isSaving: boolean;
}

/**
 * SecuritySettings allows configuration of agent security policies.
 * Includes shell command policies, workspace restrictions, and Docker isolation levels.
 */
export function SecuritySettings({
  tools,
  security,
  onSave,
  isSaving,
}: SecuritySettingsProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTools, setEditedTools] = useState<ToolsConfig | undefined>(tools);
  const [editedSecurity, setEditedSecurity] = useState<SecurityConfig | undefined>(security);

  const handleSave = () => {
    if (editedTools && editedSecurity) {
      onSave({ tools: editedTools, security: editedSecurity });
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setEditedTools(tools);
    setEditedSecurity(security);
    setIsEditing(false);
  };

  const updateToolPolicy = (policy: Partial<ShellPolicyConfig>) => {
    setEditedTools((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        exec: {
          ...prev.exec,
          policy: {
            ...prev.exec?.policy,
            ...policy,
          } as ShellPolicyConfig,
        },
      };
    });
  };

  const updateSecurity = (updates: Partial<SecurityConfig>) => {
    setEditedSecurity((prev: SecurityConfig | undefined) => ({
      ...prev,
      ...updates,
    }));
  };

  if (!tools || !security) {
    return (
      <div className="bg-claude-input rounded-xl border border-claude-border p-4">
        <p className="text-claude-text-secondary">Loading security settings...</p>
      </div>
    );
  }

  const currentPolicy = editedTools?.exec?.policy || {
    mode: "allow_all" as const,
    allow: [],
    deny: [],
    relaxed: false,
  };

  return (
    <div className="bg-claude-input rounded-xl border border-claude-border">
      <div className="px-4 py-3 border-b border-claude-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-claude-text-primary">Security</h3>
          <p className="text-xs text-claude-text-muted mt-0.5">Configure security policies and restrictions</p>
        </div>
        {isEditing ? (
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={handleCancel}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleSave} disabled={isSaving}>
              {isSaving ? "Saving..." : "Save"}
            </Button>
          </div>
        ) : (
          <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
            Edit
          </Button>
        )}
      </div>

      <div className="p-4 space-y-6">
        {/* Shell Command Policy */}
        <div>
          <h4 className="text-sm font-medium text-claude-text-primary mb-3">Shell Command Policy</h4>
          <div className="space-y-3">
            <div>
              {isEditing ? (
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={currentPolicy.relaxed ?? false}
                    onChange={(e) => updateToolPolicy({ relaxed: e.target.checked })}
                    className="rounded border-claude-border"
                  />
                  <span className="text-sm text-claude-text-secondary">Relax Shell Policy</span>
                </label>
              ) : (
                <p className="text-claude-text-primary text-sm">
                  Relax Shell Policy: {currentPolicy.relaxed ? "Enabled" : "Disabled"}
                </p>
              )}
              <p className="text-xs text-claude-text-muted mt-1">
                When enabled, allows pipes, redirects, and other shell operators that are normally blocked.
              </p>
            </div>
            <div>
              <label className="block text-xs text-claude-text-muted mb-2">Policy Mode</label>
              {isEditing ? (
                <select
                  value={currentPolicy.mode}
                  onChange={(e) => updateToolPolicy({ mode: e.target.value as ShellPolicyConfig["mode"] })}
                  className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg"
                >
                  <option value="allow_all">Allow All Commands</option>
                  <option value="deny_all">Block All Commands</option>
                  <option value="allowlist">Allowlist Only</option>
                </select>
              ) : (
                <p className="text-claude-text-primary text-sm">
                  {currentPolicy.mode === "allow_all" && "Allow All Commands"}
                  {currentPolicy.mode === "deny_all" && "Block All Commands"}
                  {currentPolicy.mode === "allowlist" && "Allowlist Only"}
                </p>
              )}
            </div>

            {currentPolicy.mode === "allowlist" && (
              <div>
                <label className="block text-xs text-claude-text-muted mb-2">Allowed Commands (one per line)</label>
                {isEditing ? (
                  <textarea
                    value={currentPolicy.allow?.join("\n") || ""}
                    onChange={(e) => updateToolPolicy({ allow: e.target.value.split("\n").filter(Boolean) })}
                    rows={4}
                    placeholder="ls&#10;cat&#10;grep&#10;python"
                    className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg font-mono"
                  />
                ) : (
                  <div className="bg-claude-surface rounded p-2">
                    {currentPolicy.allow?.length ? (
                      <ul className="text-sm text-claude-text-primary space-y-1">
                        {currentPolicy.allow.map((cmd) => (
                          <li key={cmd}>• {cmd}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-claude-text-muted text-sm">No commands in allowlist</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {(currentPolicy.mode === "allow_all" || currentPolicy.mode === "allowlist") && (
              <div>
                <label className="block text-xs text-claude-text-muted mb-2">Denied Commands (one per line)</label>
                {isEditing ? (
                  <textarea
                    value={currentPolicy.deny?.join("\n") || ""}
                    onChange={(e) => updateToolPolicy({ deny: e.target.value.split("\n").filter(Boolean) })}
                    rows={3}
                    placeholder="rm -rf&#10;sudo&#10;mkfs"
                    className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg font-mono"
                  />
                ) : (
                  <div className="bg-claude-surface rounded p-2">
                    {currentPolicy.deny?.length ? (
                      <ul className="text-sm text-claude-text-primary space-y-1">
                        {currentPolicy.deny.map((cmd) => (
                          <li key={cmd} className="text-red-600">✗ {cmd}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-claude-text-muted text-sm">No commands explicitly denied</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Workspace Restrictions */}
        <div>
          <h4 className="text-sm font-medium text-claude-text-primary mb-3">Workspace Restrictions</h4>
          <div className="space-y-2">
            {isEditing ? (
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editedTools?.restrict_to_workspace ?? true}
                  onChange={(e) =>
                    setEditedTools((prev) => (prev ? { ...prev, restrict_to_workspace: e.target.checked } : prev))
                  }
                  className="rounded border-claude-border"
                />
                <span className="text-sm text-claude-text-secondary">Restrict agent to workspace directory</span>
              </label>
            ) : (
              <p className="text-sm text-claude-text-primary">
                {editedTools?.restrict_to_workspace
                  ? "Agent is restricted to workspace directory"
                  : "Agent can access files outside workspace"}
              </p>
            )}

            {isEditing ? (
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editedTools?.ssrf_protection ?? true}
                  onChange={(e) =>
                    setEditedTools((prev) => (prev ? { ...prev, ssrf_protection: e.target.checked } : prev))
                  }
                  className="rounded border-claude-border"
                />
                <span className="text-sm text-claude-text-secondary">Enable SSRF protection for web requests</span>
              </label>
            ) : (
              <p className="text-sm text-claude-text-primary">
                {editedTools?.ssrf_protection ? "SSRF protection enabled" : "SSRF protection disabled"}
              </p>
            )}
          </div>
        </div>

        {/* Docker Isolation */}
        <div>
          <h4 className="text-sm font-medium text-claude-text-primary mb-3">Docker Isolation Level</h4>
          {isEditing ? (
            <select
              value={editedSecurity?.docker?.level || "permissive"}
              onChange={(e) => updateSecurity({ docker: { level: e.target.value as "permissive" | "sandboxed" } })}
              className="w-full px-3 py-2 border border-claude-border rounded-md text-sm bg-claude-bg"
            >
              <option value="permissive">Permissive (default)</option>
              <option value="sandboxed">Sandboxed (strict)</option>
            </select>
          ) : (
            <p className="text-sm text-claude-text-primary">
              {(editedSecurity?.docker?.level || "permissive") === "sandboxed"
                ? "Sandboxed - Read-only filesystem, no network, strict limits"
                : "Permissive - Standard container isolation"}
            </p>
          )}
          <p className="text-xs text-claude-text-muted mt-1">
            {editedSecurity?.docker?.level === "sandboxed"
              ? "Maximum security but some tools may not function correctly"
              : "Recommended for most use cases"}
          </p>
        </div>
      </div>
    </div>
  );
}
