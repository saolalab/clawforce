import { useState, useRef, useEffect } from "react";
import { Button } from "../ui";

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  source?: string;
}

interface LogsViewerProps {
  logs: LogEntry[];
  isConnected: boolean;
  error: string | null;
  onConnect: () => void;
  onDisconnect: () => void;
  onClear: () => void;
  filterLogs: (level?: string, search?: string) => LogEntry[];
}

/**
 * LogsViewer displays real-time streaming logs from the agent.
 * Supports filtering by level, searching, and auto-scrolling.
 */
export function LogsViewer({
  logs,
  isConnected,
  error,
  onConnect,
  onDisconnect,
  onClear,
  filterLogs,
}: LogsViewerProps) {
  const [levelFilter, setLevelFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const filteredLogs = filterLogs(levelFilter, searchQuery);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [filteredLogs, autoScroll]);

  // Check if user scrolled up (disable auto-scroll)
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isNearBottom);
  };

  const getLevelColor = (level: string): string => {
    switch (level.toLowerCase()) {
      case "error":
        return "text-red-600";
      case "warn":
      case "warning":
        return "text-amber-600";
      case "info":
        return "text-blue-600";
      case "debug":
        return "text-gray-500";
      default:
        return "text-gray-700";
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  return (
    <div className="bg-claude-input rounded-xl border border-claude-border flex flex-col h-[600px]">
      <div className="px-4 py-3 border-b border-claude-border space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-claude-text-primary">Logs</h3>
            <span className={`inline-flex items-center gap-1.5 text-xs ${isConnected ? "text-green-600" : "text-red-600"}`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`} />
              {isConnected ? "Live" : "Disconnected"}
            </span>
            <span className="text-xs text-claude-text-muted">{filteredLogs.length.toLocaleString()} entries</span>
          </div>
          <div className="flex gap-2">
            {isConnected ? (
              <Button variant="ghost" size="sm" onClick={onDisconnect}>
                Pause
              </Button>
            ) : (
              <Button size="sm" onClick={onConnect}>
                Resume
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={onClear}>
              Clear
            </Button>
          </div>
        </div>

        <div className="flex gap-3">
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="px-2 py-1.5 text-sm border border-claude-border rounded bg-claude-bg"
          >
            <option value="">All Levels</option>
            <option value="error">Error</option>
            <option value="warn">Warning</option>
            <option value="info">Info</option>
            <option value="debug">Debug</option>
          </select>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search logs..."
            className="flex-1 px-3 py-1.5 text-sm border border-claude-border rounded bg-claude-bg"
          />
          <label className="flex items-center gap-2 text-sm text-claude-text-secondary">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded border-claude-border"
            />
            Auto-scroll
          </label>
        </div>
      </div>

      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-auto font-mono text-xs bg-claude-bg p-4 space-y-1"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-claude-text-muted text-center py-8">
            {logs.length === 0 ? "No logs yet. Start the agent to see activity." : "No logs match the current filters."}
          </div>
        ) : (
          filteredLogs.map((entry, index) => (
            <div key={index} className="flex gap-3 py-0.5 hover:bg-claude-surface rounded px-1">
              <span className="text-gray-400 shrink-0 w-16">{formatTimestamp(entry.timestamp)}</span>
              <span className={`shrink-0 w-12 font-semibold ${getLevelColor(entry.level)}`}>
                {entry.level.toUpperCase()}
              </span>
              {entry.source && <span className="text-gray-400 shrink-0 w-20">[{entry.source}]</span>}
              <span className="text-gray-700 break-all">{entry.message}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>

      {error && !isConnected && (
        <div className="px-4 py-2 bg-red-50 border-t border-red-200">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}
    </div>
  );
}
