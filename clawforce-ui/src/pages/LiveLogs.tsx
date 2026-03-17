import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Card, PageHeader, PageContainer } from "../components/ui";
import { api, getApiBase } from "../lib/api";

export default function LiveLogs() {
  const { agentId } = useParams();
  const { token } = useAuth();
  const [logs, setLogs] = useState<{ ts: string; type: string; content: string }[]>([]);
  const [connected, setConnected] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!agentId || !token) return;
    setLogs([]);
    setConnected(false);
    let es: EventSource | null = null;
    const base = getApiBase();
    api.auth.streamToken().then((streamToken) => {
      const url = `${base}/api/agents/${agentId}/logs?token=${encodeURIComponent(streamToken)}`;
      es = new EventSource(url);
      es.onopen = () => setConnected(true);
      es.addEventListener("ping", () => setConnected(true));
      es.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          setLogs((prev) => [...prev.slice(-99), { ts: d.timestamp, type: d.event_type, content: d.content }]);
        } catch {
          setLogs((prev) => [...prev.slice(-99), { ts: "", type: "message", content: e.data }]);
        }
      };
      es.onerror = () => {
        if (es && es.readyState === EventSource.CLOSED) setConnected(false);
      };
    }).catch(() => setConnected(false));
    return () => es?.close();
  }, [agentId, token]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <PageContainer>
      <PageHeader title="Live logs" />
      <Card padding={false} className="max-h-[70vh] overflow-y-auto font-mono text-xs">
        <div className="p-3">
          {logs.length === 0 && (
            <div className="text-claude-text-muted">
              {connected ? "Connected — waiting for events..." : "Connecting to log stream..."}
            </div>
          )}
          {logs.map((l, i) => (
            <div key={i} className="border-b border-claude-surface py-1.5">
              <span className="text-claude-text-muted">{l.ts}</span>{" "}
              <span className="text-claude-accent font-medium">[{l.type}]</span>{" "}
              <span className="text-claude-text-secondary">{l.content}</span>
            </div>
          ))}
          <div ref={endRef} />
        </div>
      </Card>
    </PageContainer>
  );
}
