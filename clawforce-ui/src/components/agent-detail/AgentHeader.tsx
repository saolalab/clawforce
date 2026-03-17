import { ClawIcon } from "../ClawIcon";
import { Breadcrumb, Button } from "../ui";
import type { Agent } from "../../lib/types";

interface AgentHeaderProps {
  agent: Agent | undefined;
  isStarting: boolean;
  isStopping: boolean;
  isDeleting: boolean;
  onStart: () => void;
  onStop: () => void;
  onDelete: () => void;
}

/**
 * AgentHeader displays the agent's name, status, and control buttons.
 * Includes breadcrumb navigation and start/stop/delete actions.
 */
export function AgentHeader({
  agent,
  isStarting,
  isStopping,
  isDeleting,
  onStart,
  onStop,
  onDelete,
}: AgentHeaderProps) {
  const getStatusColor = (status: string | undefined) => {
    switch (status) {
      case "running":
        return "bg-green-50 text-green-700 ring-1 ring-green-200";
      case "stopped":
        return "bg-claude-surface text-claude-text-muted ring-1 ring-claude-border";
      case "failed":
        return "bg-red-50 text-red-700 ring-1 ring-red-200";
      case "provisioning":
      case "connecting":
        return "bg-amber-50 text-amber-700 ring-1 ring-amber-200";
      default:
        return "bg-claude-surface text-claude-text-muted ring-1 ring-claude-border";
    }
  };

  const getStatusText = (status: string | undefined) => {
    if (!status) return "Unknown";
    if (status === "stopped") return "Not connected";
    if (status === "provisioning") return "Provisioning";
    if (status === "connecting") return "Connecting";
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  return (
    <div className="mb-6">
      <Breadcrumb items={[
        { label: "Claws", to: "/claws" },
        { label: agent?.name ?? "Agent" },
      ]} />
      
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClawIcon className="h-5 w-5 shrink-0" color={agent?.color || undefined} />
          <h1 className="text-lg font-semibold text-claude-text-primary">{agent?.name}</h1>
          <span className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium ${getStatusColor(agent?.status)}`}>
            {agent?.status === "running" && (
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
              </span>
            )}
            {(agent?.status === "provisioning" || agent?.status === "connecting") && (
              <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {getStatusText(agent?.status)}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {agent?.status === "running" ? (
            <Button variant="danger" onClick={onStop} disabled={isStopping}>
              {isStopping ? "Stopping..." : "Stop"}
            </Button>
          ) : (
            <Button onClick={onStart} disabled={isStarting}>
              {isStarting ? "Starting..." : "Start"}
            </Button>
          )}
          <Button variant="ghost" onClick={onDelete} disabled={isDeleting}>
            {isDeleting ? "Deleting..." : "Delete"}
          </Button>
        </div>
      </div>
    </div>
  );
}
