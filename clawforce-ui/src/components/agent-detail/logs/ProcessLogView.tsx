import { useCallback, useEffect, useRef, useState } from "react";
import { api, getApiBase } from "../../../lib/api";
import { PROCESS_LOG_MAX } from "../constants";

export function ProcessLogView({ agentId, token }: { agentId: string; token: string }) {
  const [lines, setLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const bufRef = useRef<string[]>([]);
  const flushRef = useRef(0);

  const scheduleFlush = useCallback(() => {
    if (flushRef.current) return;
    flushRef.current = requestAnimationFrame(() => {
      flushRef.current = 0;
      setLines(bufRef.current.slice());
    });
  }, []);

  useEffect(() => {
    setLines([]);
    bufRef.current = [];
    setConnected(false);
    setError("");
    let es: EventSource | null = null;
    const base = getApiBase();
    api.auth.streamToken().then((streamToken) => {
      const url = `${base}/api/agents/${agentId}/process-logs/stream?token=${encodeURIComponent(streamToken)}`;
      es = new EventSource(url);
      es.onopen = () => setConnected(true);
      es.addEventListener("ping", () => setConnected(true));
      es.onmessage = (e) => {
        let line: string;
        try {
          const d = JSON.parse(e.data);
          line = d.line;
        } catch {
          line = e.data;
        }
        const buf = bufRef.current;
        if (buf.length >= PROCESS_LOG_MAX) buf.shift();
        buf.push(line);
        scheduleFlush();
      };
      es.onerror = () => {
        if (es && es.readyState === EventSource.CLOSED) {
          setConnected(false);
          setError("Stream disconnected");
        }
      };
    }).catch(() => { setConnected(false); setError("Failed to get stream token"); });
    return () => {
      es?.close();
      if (flushRef.current) cancelAnimationFrame(flushRef.current);
    };
  }, [agentId, token, scheduleFlush]);

  useEffect(() => {
    if (autoScroll) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines, autoScroll]);

  const ansiToHtml = (text: string) => {
    return text
      .replace(/\x1b\[(\d+)m/g, (_match, code) => {
        const c = parseInt(code);
        if (c === 0) return '</span>';
        if (c === 1) return '<span class="font-bold">';
        if (c === 31) return '<span class="text-red-400">';
        if (c === 32) return '<span class="text-green-400">';
        if (c === 33) return '<span class="text-yellow-400">';
        if (c === 34) return '<span class="text-blue-400">';
        if (c === 35) return '<span class="text-purple-400">';
        if (c === 36) return '<span class="text-cyan-400">';
        if (c === 90) return '<span class="text-gray-500">';
        return '';
      })
      .replace(/\x1b\[\d+;\d+m/g, '');
  };

  return (
    <div className="relative flex flex-col h-full p-2">
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        <label className="flex items-center gap-1.5 text-[10px] text-claude-text-muted cursor-pointer bg-black/40 rounded px-2 py-1">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="h-3 w-3 accent-claude-accent"
          />
          Auto-scroll
        </label>
      </div>
      <div className="flex-1 overflow-auto bg-[#1e1e2e] text-[#cdd6f4] p-3 rounded-lg whitespace-pre-wrap break-all leading-5 min-h-0">
        {lines.length === 0 && (
          <div
            className={
              error
                ? "text-amber-400"
                : connected
                  ? "text-emerald-400"
                  : "text-sky-400/90"
            }
          >
            {error ? error : connected ? "Connected — waiting for output..." : "Connecting to process log stream..."}
          </div>
        )}
        {lines.map((line, i) => (
          <div key={i} className="hover:bg-white/5" dangerouslySetInnerHTML={{ __html: ansiToHtml(line) }} />
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
