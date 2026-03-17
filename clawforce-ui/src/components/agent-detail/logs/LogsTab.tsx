import { useState } from "react";
import type { LogView } from "../types";
import { ActivityLogView } from "./ActivityLogView";
import { ProcessLogView } from "./ProcessLogView";

export function LogsTab({ agentId, token }: { agentId: string; token: string }) {
  const [view, setView] = useState<LogView>("activity");

  return (
    <div className="flex flex-col" style={{ height: "calc(70vh + 40px)" }}>
      <div className="mb-2 flex items-center gap-2 shrink-0">
        <div className="flex rounded-lg border border-claude-border bg-claude-surface p-0.5">
          <button
            onClick={() => setView("activity")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${view === "activity"
                ? "bg-white text-claude-text-primary shadow-sm"
                : "text-claude-text-muted hover:text-claude-text-secondary"
              }`}
          >
            Activity
          </button>
          <button
            onClick={() => setView("process")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${view === "process"
                ? "bg-white text-claude-text-primary shadow-sm"
                : "text-claude-text-muted hover:text-claude-text-secondary"
              }`}
          >
            Process Output
          </button>
        </div>
        <span className="text-[11px] text-claude-text-muted">
          {view === "activity"
            ? "Agent events (messages, tool calls, etc.)"
            : "Raw subprocess stdout/stderr (process & docker backends)"}
        </span>
      </div>

      <div
        className={`flex-1 min-h-0 rounded-xl border overflow-hidden font-mono text-xs ${view === "process"
            ? "border-[#313244] bg-[#181825]"
            : "border-claude-border bg-white"
          }`}
      >
        {view === "activity" && <ActivityLogView agentId={agentId} token={token} />}
        {view === "process" && <ProcessLogView agentId={agentId} token={token} />}
      </div>
    </div>
  );
}
