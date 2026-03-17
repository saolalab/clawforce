import { useEffect, useRef } from "react";
import { Button } from "../ui";
import "@xterm/xterm/css/xterm.css";

interface TerminalPanelProps {
  terminalRef: React.RefObject<HTMLDivElement | null>;
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  onConnect: () => void;
  onDisconnect: () => void;
  onFit: () => void;
}

/**
 * TerminalPanel provides an interactive terminal connection to the agent.
 * Uses xterm.js for a full terminal emulator experience.
 */
export function TerminalPanel({
  terminalRef,
  isConnected,
  isConnecting,
  error,
  onConnect,
  onDisconnect,
  onFit,
}: TerminalPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-fit terminal when container resizes
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver(() => {
      if (isConnected) {
        onFit();
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, [isConnected, onFit]);

  return (
    <div className="bg-claude-input rounded-xl border border-claude-border flex flex-col h-[300px]">
      <div className="px-4 py-2 border-b border-claude-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-claude-text-primary">Terminal</h3>
          <span
            className={`inline-flex items-center gap-1.5 text-xs ${
              isConnected ? "text-green-600" : isConnecting ? "text-amber-600" : "text-red-600"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? "bg-green-500" : isConnecting ? "bg-amber-500 animate-pulse" : "bg-red-500"
              }`}
            />
            {isConnected ? "Connected" : isConnecting ? "Connecting..." : error ? "Disconnected" : "Not connected"}
          </span>
        </div>
        <div className="flex gap-2">
          {isConnected ? (
            <Button variant="ghost" size="sm" onClick={onDisconnect}>
              Disconnect
            </Button>
          ) : (
            <Button size="sm" onClick={onConnect} disabled={isConnecting}>
              {isConnecting ? "Connecting..." : "Connect"}
            </Button>
          )}
        </div>
      </div>

      <div ref={containerRef} className="flex-1 overflow-hidden bg-[#1a1a2e] rounded-b-xl">
        <div ref={terminalRef} className="h-full w-full p-2" />
      </div>

      {error && !isConnected && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/90 z-10">
          <div className="text-center">
            <p className="text-red-600 mb-2">{error}</p>
            <Button onClick={onConnect} disabled={isConnecting}>
              {isConnecting ? "Connecting..." : "Retry Connection"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
