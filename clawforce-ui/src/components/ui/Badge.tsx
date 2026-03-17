const styles = {
  active: "bg-green-50 text-green-700 ring-1 ring-green-600/20",
  running: "bg-green-50 text-green-700 ring-1 ring-green-600/20",
  provisioning: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20",
  connecting: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20",
  paused: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20",
  stopped: "bg-claude-surface text-claude-text-muted ring-1 ring-claude-border",
  error: "bg-red-50 text-red-700 ring-1 ring-red-600/20",
  completed: "bg-blue-50 text-blue-700 ring-1 ring-blue-600/20",
  draft: "bg-claude-surface text-claude-text-muted ring-1 ring-claude-border",
  default: "bg-claude-surface text-claude-text-muted ring-1 ring-claude-border",
} as const;

type Props = {
  status: string;
  className?: string;
};

/** Display label for status: human-readable versions of status codes. */
function statusDisplayLabel(status: string): string {
  const labels: Record<string, string> = {
    stopped: "Not connected",
    error: "Error",
    provisioning: "Provisioning",
    connecting: "Connecting",
    draft: "Draft",
    active: "Active",
    paused: "Paused",
    completed: "Completed",
    running: "Running",
  };
  return labels[status] ?? status;
}

export default function Badge({ status, className = "" }: Props) {
  const style = styles[status as keyof typeof styles] ?? styles.default;
  const isActive = status === "active" || status === "running";
  const isTransitioning = status === "provisioning" || status === "connecting";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${style} ${className}`}>
      {isActive && (
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
        </span>
      )}
      {isTransitioning && (
        <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {statusDisplayLabel(status)}
    </span>
  );
}
