import { useState } from "react";
import { Link } from "react-router-dom";
import { ClawIcon } from "../components/ClawIcon";
import { CHANNEL_DEFS } from "../components/agent-detail/constants";
import { PageHeader, PageContainer, Badge, Button, ListCard, ListItem, PlayIcon, StopIcon, ChevronRightIcon } from "../components/ui";
import { useClaws, useStartAgent, useStopAgent } from "../lib/queries";
import CreateClawModal from "../components/CreateClawModal";

const CHANNEL_LABEL_MAP: Record<string, string> = Object.fromEntries(
  CHANNEL_DEFS.map((c) => [c.key, c.label])
);

export default function ClawsList() {
  const { data: claws = [] } = useClaws();
  const [modalOpen, setModalOpen] = useState(false);
  const startAgent = useStartAgent();
  const stopAgent = useStopAgent();

  return (
    <PageContainer>
      <PageHeader
        title="Claws"
        icon={<ClawIcon className="h-5 w-5" />}
        description="Create and manage your claws."
        action={
          <Button onClick={() => setModalOpen(true)}>
            <ClawIcon className="mr-1.5 h-4 w-4" color="white" />
            Add Claw
          </Button>
        }
      />

      <ListCard emptyMessage='No claws yet. Click "Add Claw" to create one.'>
        {claws.map((claw) => {
          const isRunning = claw.status === "running";
          const isTransitioning = claw.status === "provisioning" || claw.status === "connecting";
          return (
            <ListItem
              key={claw.id}
              actions={
                <>
                  {claw.channels_enabled && claw.channels_enabled.length > 0 && (
                    <div className="flex items-center gap-1.5 mr-2">
                      {claw.channels_enabled.slice(0, 3).map((ch) => {
                        const label = CHANNEL_LABEL_MAP[ch] || ch;
                        return (
                          <span
                            key={ch}
                            className="rounded px-1.5 py-px text-[10px] font-medium bg-claude-surface text-claude-text-secondary ring-1 ring-claude-border"
                          >
                            {label}
                          </span>
                        );
                      })}
                      {claw.channels_enabled.length > 3 && (
                        <span className="text-[10px] text-claude-text-muted">…</span>
                      )}
                    </div>
                  )}
                  <div className="flex items-center gap-1.5">
                {isRunning ? (
                  <button
                    onClick={() => stopAgent.mutate(claw.id)}
                    disabled={stopAgent.isPending}
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-red-600 bg-red-50 ring-1 ring-red-600/20 hover:bg-red-100 transition-colors disabled:opacity-50"
                  >
                    <StopIcon className="h-2.5 w-2.5" />
                    Stop
                  </button>
                ) : isTransitioning ? (
                  <span className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-amber-600 bg-amber-50 ring-1 ring-amber-600/20 opacity-75">
                    <svg className="h-2.5 w-2.5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Starting
                  </span>
                ) : (
                  <button
                    onClick={() => startAgent.mutate(claw.id)}
                    disabled={startAgent.isPending}
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-green-700 bg-green-50 ring-1 ring-green-600/20 hover:bg-green-100 transition-colors disabled:opacity-50"
                  >
                    <PlayIcon className="h-2.5 w-2.5" />
                    Start
                  </button>
                )}
                    <Link
                      to={`/agents/${claw.id}`}
                      className="rounded p-1 text-claude-border-strong hover:text-claude-accent hover:bg-claude-surface transition-all"
                    >
                      <ChevronRightIcon className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </>
              }
            >
              <div
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors"
                style={{
                  backgroundColor: claw.color ? `${claw.color}18` : undefined,
                }}
              >
                <ClawIcon className="h-3.5 w-3.5" color={claw.color || undefined} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <Link
                    to={`/agents/${claw.id}`}
                    className="text-sm font-medium text-claude-text-primary hover:text-claude-accent transition-colors truncate"
                  >
                    {claw.name}
                  </Link>
                  <Badge status={claw.status} />
                </div>
              </div>
            </ListItem>
          );
        })}
      </ListCard>

      <CreateClawModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </PageContainer>
  );
}
