import { useEffect, useRef, useState, useCallback } from "react";
import { getApiBase } from "../../../lib/api";

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  source?: string;
}

/**
 * Hook for streaming agent logs via Server-Sent Events.
 * Provides real-time log updates with filtering and search capabilities.
 */
export function useLogs(agentId: string | undefined) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const bufferRef = useRef<LogEntry[]>([]);
  const flushIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const flushBuffer = useCallback(() => {
    if (bufferRef.current.length > 0) {
      setLogs((prev) => {
        const combined = [...prev, ...bufferRef.current];
        // Keep only last 10,000 entries for performance
        return combined.slice(-10000);
      });
      bufferRef.current = [];
    }
  }, []);

  const connect = useCallback(() => {
    if (!agentId) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Clear existing logs when reconnecting
    setLogs([]);
    bufferRef.current = [];
    setError(null);

    // Start flush interval for batching updates
    flushIntervalRef.current = setInterval(flushBuffer, 250);

    const url = `${getApiBase()}/agents/${agentId}/logs/stream`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const entry: LogEntry = {
          timestamp: data.timestamp || new Date().toISOString(),
          level: data.level || "info",
          message: data.message || String(data),
          source: data.source || "agent",
        };
        bufferRef.current.push(entry);
      } catch {
        // Fallback for plain text logs
        bufferRef.current.push({
          timestamp: new Date().toISOString(),
          level: "info",
          message: event.data,
          source: "agent",
        });
      }
    };

    es.onerror = () => {
      setIsConnected(false);
      setError("Log stream connection failed");
    };
  }, [agentId, flushBuffer]);

  const disconnect = useCallback(() => {
    if (flushIntervalRef.current) {
      clearInterval(flushIntervalRef.current);
      flushIntervalRef.current = null;
    }
    flushBuffer(); // Flush remaining buffer
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setIsConnected(false);
  }, [flushBuffer]);

  const clear = useCallback(() => {
    setLogs([]);
    bufferRef.current = [];
  }, []);

  const filterLogs = useCallback(
    (level?: string, search?: string) => {
      return logs.filter((entry) => {
        const levelMatch = !level || entry.level === level;
        const searchMatch =
          !search ||
          entry.message.toLowerCase().includes(search.toLowerCase()) ||
          entry.source?.toLowerCase().includes(search.toLowerCase());
        return levelMatch && searchMatch;
      });
    },
    [logs]
  );

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    logs,
    isConnected,
    error,
    connect,
    disconnect,
    clear,
    filterLogs,
  };
}
