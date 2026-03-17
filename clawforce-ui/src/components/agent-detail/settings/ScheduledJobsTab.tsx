import { useWorkspaceFile } from "../../../lib/queries";
import { Section } from "../ui/Section";
import { formatSchedule, relativeTime } from "../utils";
import type { CronJobData } from "../types";

function CronJobsSection({ agentId }: { agentId: string }) {
  const { data: raw } = useWorkspaceFile(agentId, "profiles/crons/jobs.json");
  const jobs: CronJobData[] = (() => {
    if (!raw) return [];
    try { return (JSON.parse(raw) as { jobs?: CronJobData[] }).jobs ?? []; } catch { return []; }
  })();

  if (jobs.length === 0) {
    return (
      <p className="text-xs text-claude-text-muted">
        No scheduled jobs. The agent can create them via the <code className="bg-claude-surface px-1 rounded text-[11px]">cron</code> tool.
      </p>
    );
  }

  return (
    <div className="space-y-1.5">
      {jobs.map((j) => {
        const statusColor = j.state.lastStatus === "error" ? "text-red-500" : j.state.lastStatus === "ok" ? "text-green-600" : "text-claude-text-muted";
        return (
          <div key={j.id} className="flex items-start gap-3 rounded-lg border border-claude-border bg-claude-bg px-3 py-2">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${j.enabled ? "bg-green-500" : "bg-claude-border-strong"}`} />
                <span className="text-sm font-medium text-claude-text-primary truncate">{j.name}</span>
                <span className={`rounded px-1.5 py-px text-[10px] font-medium ${j.schedule.kind === "cron" ? "bg-purple-50 text-purple-700 ring-1 ring-purple-200"
                    : j.schedule.kind === "at" ? "bg-blue-50 text-blue-700 ring-1 ring-blue-200"
                      : "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                  }`}>
                  {j.schedule.kind}
                </span>
                {j.deleteAfterRun && (
                  <span className="rounded px-1.5 py-px text-[10px] font-medium bg-gray-50 text-gray-500 ring-1 ring-gray-200">once</span>
                )}
              </div>
              <p className="mt-0.5 text-xs text-claude-text-muted truncate">{j.payload.message}</p>
            </div>
            <div className="shrink-0 text-right text-[11px] space-y-0.5">
              <div className="font-mono text-claude-text-secondary">{formatSchedule(j.schedule)}</div>
              {j.schedule.tz && <div className="text-claude-text-muted">{j.schedule.tz}</div>}
              <div className="flex items-center justify-end gap-1.5">
                {j.state.nextRunAtMs && <span className="text-claude-text-muted">next: {relativeTime(j.state.nextRunAtMs)}</span>}
                {j.state.lastStatus && <span className={statusColor}>{j.state.lastStatus}</span>}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ScheduledJobsTab({ agentId }: { agentId: string }) {
  return (
    <Section title="Scheduled Jobs">
      <p className="text-xs text-claude-text-muted mb-2.5">
        Cron jobs from <code className="bg-claude-surface px-1 rounded text-[11px]">profiles/crons/jobs.json</code>.
      </p>
      <CronJobsSection agentId={agentId} />
    </Section>
  );
}
