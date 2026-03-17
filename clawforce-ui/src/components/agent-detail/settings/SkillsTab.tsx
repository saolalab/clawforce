import { useAgentSkills } from "../../../lib/queries";
import { Section, Toggle } from "../ui/Section";
import type { Agent, SkillInfo } from "../types";

export function SkillsTab({
  agentId,
  agent,
  updateSkills,
}: {
  agentId: string;
  agent: Agent;
  updateSkills: (disabled: string[]) => void;
}) {
  const { data: skills, isLoading } = useAgentSkills(agentId);
  const disabledSet = new Set(agent.skills?.disabled ?? []);

  function toggle(name: string, enabled: boolean) {
    const next = new Set(disabledSet);
    if (enabled) {
      next.delete(name);
    } else {
      next.add(name);
    }
    updateSkills([...next]);
  }

  function SkillRow({ skill }: { skill: SkillInfo }) {
    const isEnabled = !disabledSet.has(skill.name);
    return (
      <div className={`flex items-center justify-between rounded-lg border border-claude-border bg-claude-bg px-3 py-2.5 ${!skill.available ? "opacity-60" : ""}`}>
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-base shrink-0 w-6 text-center">{skill.emoji || "🔧"}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-claude-text-primary">{skill.name}</span>
              {skill.always && (
                <span className="rounded px-1.5 py-px text-[10px] font-medium bg-blue-50 text-blue-700 ring-1 ring-blue-200">always</span>
              )}
              {!skill.available && (
                <span className="rounded px-1.5 py-px text-[10px] font-medium bg-amber-50 text-amber-700 ring-1 ring-amber-200">deps missing</span>
              )}
              <span className={`rounded px-1.5 py-px text-[10px] font-medium ${skill.source === "workspace"
                  ? "bg-purple-50 text-purple-700 ring-1 ring-purple-200"
                  : "bg-gray-50 text-gray-500 ring-1 ring-gray-200"
                }`}>
                {skill.source}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-claude-text-muted truncate">{skill.description}</p>
          </div>
        </div>
        <Toggle
          checked={isEnabled}
          onChange={(v) => toggle(skill.name, v)}
          label=""
        />
      </div>
    );
  }

  const builtinSkills = (skills ?? []).filter((s: SkillInfo) => s.source === "builtin");
  const workspaceSkills = (skills ?? []).filter((s: SkillInfo) => s.source === "workspace");

  return (
    <div className="space-y-3">
      {isLoading && <p className="text-xs text-claude-text-muted">Loading skills…</p>}

      {!isLoading && (!skills || skills.length === 0) && (
        <Section title="Skills">
          <p className="text-xs text-claude-text-muted">
            No skills found. Start the agent to provision workspace skills, or install from the{" "}
            <a href="/marketplace" className="text-claude-accent hover:underline">Marketplace</a>.
          </p>
        </Section>
      )}

      {workspaceSkills.length > 0 && (
        <Section title="Workspace Skills">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-claude-text-muted">Toggle skills on/off to control agent capabilities.</p>
            <a
              href="/marketplace"
              className="text-sm text-claude-accent hover:underline font-medium inline-flex items-center gap-1"
            >
              Browse Marketplace
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </a>
          </div>
          <div className="space-y-1.5">
            {workspaceSkills.map((s: SkillInfo) => <SkillRow key={s.name} skill={s} />)}
          </div>
        </Section>
      )}

      {builtinSkills.length > 0 && (
        <Section title="Built-in Skills">
          {workspaceSkills.length === 0 && (
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-claude-text-muted">Toggle skills on/off to control agent capabilities.</p>
              <a
                href="/marketplace"
                className="text-sm text-claude-accent hover:underline font-medium inline-flex items-center gap-1"
              >
                Browse Marketplace
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </a>
            </div>
          )}
          <div className="space-y-1.5">
            {builtinSkills.map((s: SkillInfo) => <SkillRow key={s.name} skill={s} />)}
          </div>
        </Section>
      )}
    </div>
  );
}
