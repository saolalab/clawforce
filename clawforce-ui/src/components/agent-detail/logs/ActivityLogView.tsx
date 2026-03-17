import { useCallback, useEffect, useRef, useState } from "react";
import { api, getApiBase } from "../../../lib/api";
import { ACTIVITY_BUFFER_MAX, ACTIVITY_FILTERS } from "../constants";
import { formatActivityTime, getEventConfig } from "../utils";
import type { ActivityEntry, ActivityFilter } from "../types";

function ToolEventRow({ entry, result }: { entry: ActivityEntry; result?: ActivityEntry }) {
  const [expanded, setExpanded] = useState(false);
  const hasResult = result && result.content;
  const isError = result?.resultStatus === "error";

  return (
    <div className="group">
      <div className="flex items-center gap-2 py-1 px-3 hover:bg-claude-surface/50 transition-colors rounded-md">
        <span className="shrink-0 w-[62px] text-[10px] tabular-nums text-claude-text-muted font-mono">
          {formatActivityTime(entry.ts)}
        </span>
        {entry.toolName && (
          <span className="shrink-0 rounded bg-violet-50 border border-violet-200 px-1.5 py-0.5 text-[10px] font-semibold font-mono text-violet-700">
            {entry.toolName}
          </span>
        )}
        {entry.content && (
          <span className="flex-1 min-w-0 text-[11px] font-mono text-claude-text-muted truncate" title={entry.content}>
            {entry.content}
          </span>
        )}
        {hasResult && (
          <button
            onClick={() => setExpanded(!expanded)}
            className={`shrink-0 text-[10px] transition-colors ${isError
                ? "text-red-500 hover:text-red-600"
                : "text-claude-text-muted hover:text-claude-accent"
              }`}
          >
            {expanded ? "hide" : "show"}
          </button>
        )}
        {result && (
          <span className={`shrink-0 h-1.5 w-1.5 rounded-full ${isError ? "bg-red-500" : "bg-green-500"}`} />
        )}
      </div>
      {expanded && hasResult && (
        <div className="ml-[86px] mr-3 mt-1 mb-2 rounded border border-claude-border bg-claude-surface/50 p-2">
          <pre className={`text-[10px] font-mono whitespace-pre-wrap break-words max-h-40 overflow-auto ${isError ? "text-red-600" : "text-claude-text-secondary"}`}>
            {result.content}
          </pre>
        </div>
      )}
    </div>
  );
}

function ActivityEventRow({ entry, result }: { entry: ActivityEntry; result?: ActivityEntry }) {
  const cfg = getEventConfig(entry.type);
  const isError = entry.resultStatus === "error";
  const [expanded, setExpanded] = useState(false);

  if (entry.type === "tool_call") {
    return <ToolEventRow entry={entry} result={result} />;
  }

  if (entry.type === "tool_result") {
    return null;
  }

  const isLong = entry.content.length > 120;
  const displayContent = !expanded && isLong ? entry.content.slice(0, 120).trimEnd() + "…" : entry.content;

  return (
    <div className="group flex items-start gap-2.5 py-1.5 px-3 hover:bg-claude-surface/50 transition-colors rounded-md">
      <span className="shrink-0 w-[62px] text-[10px] tabular-nums text-claude-text-muted pt-0.5 font-mono">
        {formatActivityTime(entry.ts)}
      </span>

      <span className={`shrink-0 inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium leading-none ${cfg.bg} ${cfg.color}`}>
        <span className="text-[9px]">{cfg.icon}</span>
        {cfg.label}
      </span>

      <span className={`flex-1 min-w-0 text-xs leading-relaxed ${isError ? "text-red-600" : "text-claude-text-secondary"}`}>
        {isLong ? (
          <button onClick={() => setExpanded(!expanded)} className="text-left w-full">
            <span className="break-words">{displayContent}</span>
            <span className="text-[10px] text-claude-text-muted ml-1 hover:text-claude-accent transition-colors">
              {expanded ? "[less]" : "[more]"}
            </span>
          </button>
        ) : (
          <span className="break-words">{entry.content}</span>
        )}
      </span>
    </div>
  );
}

export function ActivityLogView({ agentId, token }: { agentId: string; token: string }) {
  const [logs, setLogs] = useState<ActivityEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState<ActivityFilter>("all");
  const [search, setSearch] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [paused, setPaused] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const bufferRef = useRef<ActivityEntry[]>([]);
  const flushRef = useRef(0);
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  const scheduleFlush = useCallback(() => {
    if (flushRef.current) return;
    flushRef.current = requestAnimationFrame(() => {
      flushRef.current = 0;
      if (!pausedRef.current) setLogs(bufferRef.current.slice());
    });
  }, []);

  useEffect(() => {
    setLogs([]);
    bufferRef.current = [];
    setConnected(false);
    let es: EventSource | null = null;
    const base = getApiBase();
    api.auth.streamToken().then((streamToken) => {
      const url = `${base}/api/agents/${agentId}/logs?token=${encodeURIComponent(streamToken)}`;
      es = new EventSource(url);
      es.onopen = () => setConnected(true);
      es.addEventListener("ping", () => setConnected(true));
      es.onmessage = (e) => {
        let entry: ActivityEntry;
        try {
          const d = JSON.parse(e.data);
          entry = {
            ts: d.timestamp ?? "",
            type: d.event_type ?? "activity",
            content: d.content ?? "",
            channel: d.channel ?? "",
            toolName: d.tool_name,
            resultStatus: d.result_status,
            durationMs: d.duration_ms,
            eventId: d.event_id,
          };
        } catch {
          entry = { ts: "", type: "message", content: e.data, channel: "" };
        }
        const buf = bufferRef.current;
        if (entry.eventId && buf.some((x) => x.eventId === entry.eventId)) return;
        if (buf.length >= ACTIVITY_BUFFER_MAX) {
          buf.shift();
        }
        buf.push(entry);
        scheduleFlush();
      };
      es.onerror = () => {
        if (es && es.readyState === EventSource.CLOSED) setConnected(false);
      };
    }).catch(() => setConnected(false));
    return () => {
      es?.close();
      if (flushRef.current) cancelAnimationFrame(flushRef.current);
    };
  }, [agentId, token, scheduleFlush]);

  useEffect(() => {
    if (!paused) {
      setLogs(bufferRef.current.slice());
    }
  }, [paused]);

  useEffect(() => {
    if (autoScroll && !paused) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, autoScroll, paused]);

  const filtered = logs.filter((l) => {
    if (filter !== "all") {
      const cfg = getEventConfig(l.type);
      if (cfg.group !== filter && cfg.group !== "all") return false;
    }
    if (search) {
      const q = search.toLowerCase();
      return (
        l.content.toLowerCase().includes(q) ||
        l.type.toLowerCase().includes(q) ||
        (l.toolName ?? "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const counts = {
    total: logs.length,
    errors: logs.filter((l) => l.resultStatus === "error").length,
  };

  const agentNotConnected = logs.some(
    (l) =>
      l.type === "status" &&
      (l.content.toLowerCase().includes("agent not connected") ||
        l.content.toLowerCase().includes("waiting for websocket"))
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-claude-border bg-white/50">
        <div className="flex rounded-md border border-claude-border bg-claude-surface p-0.5">
          {ACTIVITY_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${filter === f.key
                  ? "bg-white text-claude-text-primary shadow-sm"
                  : "text-claude-text-muted hover:text-claude-text-secondary"
                }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="relative flex-1 max-w-xs">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter events…"
            className="w-full rounded-md border border-claude-border bg-white px-2.5 py-1 text-[11px] text-claude-text-secondary placeholder:text-claude-text-muted focus:outline-none focus:ring-1 focus:ring-claude-accent/40 focus:border-claude-accent"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-claude-text-muted hover:text-claude-text-secondary text-xs"
            >
              ✕
            </button>
          )}
        </div>

        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-2 text-[10px] tabular-nums text-claude-text-muted">
            <span>{counts.total} events</span>
            {counts.errors > 0 && <span className="text-red-500">{counts.errors} errors</span>}
          </div>

          <button
            onClick={() => {
              if (paused) setLogs([...bufferRef.current]);
              setPaused(!paused);
            }}
            className={`rounded px-2 py-0.5 text-[10px] font-medium border transition-colors ${paused
                ? "border-amber-300 bg-amber-50 text-amber-700"
                : "border-claude-border bg-white text-claude-text-muted hover:text-claude-text-secondary"
              }`}
          >
            {paused ? "▶ Resume" : "⏸ Pause"}
          </button>

          <label className="flex items-center gap-1 text-[10px] text-claude-text-muted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="h-3 w-3 accent-claude-accent"
            />
            Auto-scroll
          </label>

          <span className="flex items-center gap-2 text-[10px] text-claude-text-muted">
            <span className="flex items-center gap-1">
              <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-green-500" : "bg-claude-border-strong"}`} />
              {connected ? "Live" : "Disconnected"}
            </span>
            {connected && agentNotConnected && (
              <span className="text-amber-600" title="Log stream is connected; agent worker has not registered with the control plane yet">
                Agent connecting…
              </span>
            )}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 py-1">
        {filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="text-2xl mb-2 text-claude-border-strong">
              {logs.length === 0 ? "◎" : "⊘"}
            </div>
            <p className="text-xs text-claude-text-muted">
              {logs.length === 0
                ? connected
                  ? "Stream connected. Send a message to the agent or trigger an action to see activity."
                  : "Connecting to log stream…"
                : "No events match the current filter."}
            </p>
          </div>
        )}
        {filtered.map((l, i) => {
          let result: ActivityEntry | undefined;
          if (l.type === "tool_call") {
            const next = filtered[i + 1];
            if (next?.type === "tool_result" && next.toolName === l.toolName) {
              result = next;
            }
          }
          return <ActivityEventRow key={l.eventId ?? i} entry={l} result={result} />;
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
}
