import { useEffect, useRef, useCallback, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { getApiBase } from "../../../lib/api";

interface TerminalMessage {
  type: "output" | "error" | "exit";
  data?: string;
  code?: number;
}

/**
 * Hook for managing an xterm.js terminal connection to an agent.
 * Handles WebSocket connection, terminal lifecycle, and command execution.
 */
export function useTerminal(agentId: string | undefined) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(() => {
    if (!agentId || !terminalRef.current) return;

    setIsConnecting(true);
    setError(null);

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    // Initialize xterm
    if (!xtermRef.current) {
      xtermRef.current = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: 'Menlo, Monaco, "Courier New", monospace',
        theme: {
          background: "#1a1a2e",
          foreground: "#eaeaea",
          cursor: "#f39c12",
          selectionBackground: "#34495e",
        },
        cols: 80,
        rows: 24,
      });

      fitAddonRef.current = new FitAddon();
      xtermRef.current.loadAddon(fitAddonRef.current);
      xtermRef.current.open(terminalRef.current);

      // Handle terminal input
      xtermRef.current.onData((data) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "input", data }));
        }
      });
    }

    // Connect WebSocket
    const wsUrl = `${getApiBase().replace(/^http/, "ws")}/agents/${agentId}/terminal`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setIsConnecting(false);
      xtermRef.current?.writeln("\r\n\x1b[32mConnected to agent terminal\x1b[0m\r\n");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as TerminalMessage;
        if (msg.type === "output" && msg.data) {
          xtermRef.current?.write(msg.data);
        } else if (msg.type === "error" && msg.data) {
          xtermRef.current?.writeln(`\r\n\x1b[31mError: ${msg.data}\x1b[0m\r\n`);
        } else if (msg.type === "exit") {
          xtermRef.current?.writeln(`\r\n\x1b[33mProcess exited with code ${msg.code}\x1b[0m\r\n`);
        }
      } catch {
        // Raw output
        xtermRef.current?.write(event.data);
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection error");
      setIsConnected(false);
      setIsConnecting(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsConnecting(false);
      xtermRef.current?.writeln("\r\n\x1b[31mDisconnected from terminal\x1b[0m\r\n");
    };
  }, [agentId]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  const sendCommand = useCallback((command: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "command", data: command }));
    }
  }, []);

  const fit = useCallback(() => {
    fitAddonRef.current?.fit();
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
      xtermRef.current?.dispose();
      xtermRef.current = null;
    };
  }, [disconnect]);

  return {
    terminalRef,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    sendCommand,
    fit,
  };
}
