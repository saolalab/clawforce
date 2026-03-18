import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { api } from "../../../lib/api";

export function TerminalPanel({
  agentId,
  token,
  onClose,
}: {
  agentId: string;
  token: string;
  onClose: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<{ terminal: Terminal; fitAddon: FitAddon } | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current || !token) return;

    const term = new Terminal({
      theme: {
        background: "#1e1e1e",
        foreground: "#d4d4d4",
        cursor: "#d4d4d4",
        cursorAccent: "#1e1e1e",
        selectionBackground: "#264f78",
        black: "#1e1e1e",
        red: "#f44747",
        green: "#6a9955",
        yellow: "#dcdcaa",
        blue: "#569cd6",
        magenta: "#c586c0",
        cyan: "#4ec9b0",
        white: "#d4d4d4",
      },
      fontFamily: "Menlo, Monaco, 'Courier New', monospace",
      fontSize: 12,
      cursorBlink: true,
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(containerRef.current);
    fitAddon.fit();
    terminalRef.current = { terminal: term, fitAddon };

    let ws: WebSocket | null = null;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

    api.auth.streamToken().then((streamToken) => {
      const wsUrl = `${protocol}//${window.location.host}/api/agents/${agentId}/terminal?token=${encodeURIComponent(streamToken)}`;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setConnected(true);
        fitAddon.fit();
        if (term.cols && term.rows) {
          ws!.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
        }
      };
      ws.onclose = () => setConnected(false);
      ws.onerror = () => setError("Connection error");

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "output" && typeof msg.data === "string") {
            term.write(msg.data);
          }
          if (msg.type === "error") {
            setError(msg.data ?? "Error");
          }
        } catch {
          term.write(event.data);
        }
      };

      term.onData((data) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "input", data }));
        }
      });
    }).catch(() => setError("Failed to get stream token"));

    const onResize = () => {
      fitAddon.fit();
      if (ws && ws.readyState === WebSocket.OPEN && terminalRef.current) {
        const { cols, rows } = term;
        ws.send(JSON.stringify({ type: "resize", cols, rows }));
      }
    };
    window.addEventListener("resize", onResize);

    const ro = new ResizeObserver(onResize);
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      window.removeEventListener("resize", onResize);
      ws?.close();
      term.dispose();
      terminalRef.current = null;
    };
  }, [agentId, token]);

  return (
    <div className="flex flex-col h-full min-h-0 bg-[#1e1e1e] rounded-b-lg">
      <div className="flex items-center justify-between flex-shrink-0 px-2 py-1 border-b border-claude-border bg-claude-surface/80">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-claude-text-secondary">Terminal</span>
          {error && <span className="text-xs text-red-600">{error}</span>}
          {!error && (
            <span className={`text-[10px] ${connected ? "text-green-600" : "text-claude-text-muted"}`}>
              {connected ? "Connected" : "Connecting…"}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded text-claude-text-muted hover:text-claude-text-primary hover:bg-claude-sidebar-hover"
          aria-label="Close terminal"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div ref={containerRef} className="flex-1 min-h-0 w-full p-2" />
    </div>
  );
}
