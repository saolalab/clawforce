import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { marked } from "marked";
import DOMPurify from "dompurify";
import {
  PageHeader,
  PageContainer,
  Badge,
  Button,
  PlanIcon,
  PlayIcon,
  StopIcon,
  PeopleIcon,
  PencilIcon,
  TrashIcon,
  CheckIcon,
} from "../components/ui";
import {
  usePlan,
  useClaws,
  useUpdateTask,
  useDeleteTask,
  useAssignAgent,
  useRemoveAgent,
  useActivatePlan,
  useDeactivatePlan,
  useCompletePlan,
  usePlanArtifacts,
  useUploadArtifact,
  useDeleteArtifact,
  useRenameArtifact,
  useMoveArtifact,
} from "../lib/queries";
import { api, getApiBase } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import type { PlanColumn as PlanColumnType, PlanTask as PlanTaskType, PlanArtifact, AgentSummary, InboxEvent } from "../lib/types";
import { ClawIcon } from "../components/ClawIcon";
import Modal from "../components/Modal";
import CreateTaskModal from "../components/CreateTaskModal";
import EditTaskModal from "../components/EditTaskModal";
import TaskDetailModal from "../components/TaskDetailModal";

marked.setOptions({ breaks: true, gfm: true });

function renderMarkdown(raw: string): string {
  return DOMPurify.sanitize(marked.parse(raw) as string);
}

const MAX_EVENTS = 300;
const DISPLAY_LIMIT = 50;

type EventMeta = { label: string; summary: string; isLifecycle: boolean };

const EVENT_LABELS: Record<string, EventMeta> = {
  message_received: { label: "Message", summary: "Received a message", isLifecycle: false },
  message_sent: { label: "Activity", summary: "Sent a response", isLifecycle: false },
  tool_call: { label: "Tool", summary: "Called a tool", isLifecycle: false },
  tool_result: { label: "Tool", summary: "Tool returned", isLifecycle: false },
  agent_started: { label: "Started", summary: "Agent started", isLifecycle: true },
  agent_stopped: { label: "Stopped", summary: "Agent stopped", isLifecycle: true },
  task_status_changed: { label: "Task", summary: "Task status changed", isLifecycle: true },
  task_comment: { label: "Comment", summary: "Added a comment", isLifecycle: true },
};

function getEventDisplay(eventType: string): EventMeta {
  return EVENT_LABELS[eventType] ?? { label: "Activity", summary: "", isLifecycle: false };
}

function formatRelative(iso: string): string {
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffSec = Math.floor(diffMs / 1_000);
  if (diffSec < 60) return "now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

const PROSE_CLASSES = `prose prose-xs prose-invert max-w-none text-xs text-claude-text-secondary
  [&_p]:my-0.5 [&_ul]:my-0.5 [&_ol]:my-0.5 [&_li]:my-0 [&_code]:text-[11px]
  [&_code]:bg-claude-surface [&_code]:px-1 [&_code]:rounded [&_strong]:text-claude-text-primary
  [&_h1]:text-sm [&_h2]:text-xs [&_h3]:text-xs [&_pre]:bg-claude-surface [&_pre]:p-2 [&_pre]:rounded-md
  [&_a]:text-claude-accent [&_a]:no-underline hover:[&_a]:underline`;

function TimelineEventContent({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);
  const html = renderMarkdown(content);
  const isLong = content.length > 160;
  const preview = isLong ? content.slice(0, 160).trimEnd() + "..." : content;

  if (!isLong) {
    return <div className={PROSE_CLASSES} dangerouslySetInnerHTML={{ __html: html }} />;
  }

  return expanded ? (
    <div>
      <div className={PROSE_CLASSES} dangerouslySetInnerHTML={{ __html: html }} />
      <button
        onClick={() => setExpanded(false)}
        className="text-[10px] text-claude-text-muted hover:text-claude-accent transition-colors mt-1"
      >
        Show less
      </button>
    </div>
  ) : (
    <button onClick={() => setExpanded(true)} className="text-left w-full group/expand">
      <p className="text-xs text-claude-text-muted group-hover/expand:text-claude-text-secondary transition-colors leading-relaxed">
        {preview}
      </p>
    </button>
  );
}

function TimelineLifecycleEvent({ ev, meta }: { ev: InboxEvent; meta: EventMeta }) {
  const isStarted = ev.event_type === "agent_started";
  const isTask = ev.event_type === "task_status_changed";
  const isComment = ev.event_type === "task_comment";
  const color = ev.agent_color || undefined;

  if (isTask || isComment) {
    return (
      <div className="relative flex items-start gap-3 py-2">
        <div className="relative z-10 flex w-8 shrink-0 items-center justify-center pt-1.5">
          <div className={`flex h-6 w-6 items-center justify-center rounded-full ${isComment ? "bg-purple-100 text-purple-600" : "bg-blue-100 text-blue-600"}`}>
            {isComment ? (
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            ) : (
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            )}
          </div>
        </div>
        <div className="flex-1 min-w-0 rounded-lg border border-claude-border/60 bg-white/50 px-3 py-2">
          <div className="flex items-center gap-2 mb-0.5">
            <Link to={`/agents/${ev.agent_id}`} className="text-xs font-medium text-claude-text-primary hover:text-claude-accent transition-colors">
              {ev.agent_name}
            </Link>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${isComment ? "bg-purple-50 text-purple-600" : "bg-blue-50 text-blue-600"}`}>
              {isComment ? "comment" : "status"}
            </span>
            <span className="text-[10px] text-claude-text-muted tabular-nums ml-auto shrink-0">{formatRelative(ev.timestamp)}</span>
          </div>
          {ev.content && <TimelineEventContent content={ev.content} />}
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex items-center gap-3 py-2">
      <div className="relative z-10 flex w-8 shrink-0 items-center justify-center">
        <span className={`h-2.5 w-2.5 rounded-full ring-[3px] ring-claude-input ${isStarted ? "bg-green-500" : "bg-claude-border-strong"}`} />
      </div>
      <div className="flex flex-1 items-center gap-2 min-w-0">
        <ClawIcon className="h-4 w-4 shrink-0" color={color} />
        <span className="text-xs font-medium text-claude-text-secondary">
          {ev.agent_name}
        </span>
        <span className="text-[11px] text-claude-text-muted">{meta.summary}</span>
        <span className="text-[10px] text-claude-text-muted tabular-nums ml-auto shrink-0">{formatTime(ev.timestamp)}</span>
      </div>
    </div>
  );
}

function TimelineContentEvent({ ev }: { ev: InboxEvent; meta: EventMeta }) {
  const { summary } = getEventDisplay(ev.event_type);
  const color = ev.agent_color || undefined;
  return (
    <div className="relative flex items-start gap-3 py-2">
      <div className="relative z-10 flex w-8 shrink-0 items-center justify-center pt-1.5">
        <ClawIcon className="h-6 w-6" color={color} />
      </div>
      <div className="flex-1 min-w-0 rounded-lg border border-claude-border/60 bg-white/50 px-3 py-2">
        <div className="flex items-center gap-2 mb-0.5">
          <Link to={`/agents/${ev.agent_id}`} className="text-xs font-medium text-claude-text-primary hover:text-claude-accent transition-colors">
            {ev.agent_name}
          </Link>
          <span className="text-[10px] text-claude-text-muted tabular-nums ml-auto shrink-0">{formatRelative(ev.timestamp)}</span>
        </div>
        {ev.content ? (
          <TimelineEventContent content={ev.content} />
        ) : summary ? (
          <p className="text-xs text-claude-text-muted">{summary}</p>
        ) : null}
      </div>
    </div>
  );
}

const BASE_LABELS = new Set(["Started", "Stopped", "Activity", "Task", "Comment"]);

function PlanTimeline({
  planId,
  agents,
  planStatus,
}: {
  planId: string;
  agents: AgentSummary[];
  planStatus: string;
}) {
  const { token } = useAuth();
  const [events, setEvents] = useState<InboxEvent[]>([]);
  const [showTool, setShowTool] = useState(false);
  const [showMessage, setShowMessage] = useState(false);
  const [connected, setConnected] = useState(false);
  const eventIdRef = useRef(0);

  const bufRef = useRef<InboxEvent[]>([]);
  const seenRef = useRef(new Set<string>());
  const flushRef = useRef(0);

  const scheduleFlush = useCallback(() => {
    if (flushRef.current) return;
    flushRef.current = requestAnimationFrame(() => {
      flushRef.current = 0;
      setEvents(bufRef.current.slice());
    });
  }, []);

  const addEvent = useCallback(
    (raw: { agent_id?: string; timestamp?: string; event_type?: string; content?: string }) => {
      const agentId = raw.agent_id ?? "";
      const ts = raw.timestamp ?? new Date().toISOString();
      const eventType = raw.event_type ?? "activity";
      const content = raw.content ?? "";
      const sig = `${agentId}:${eventType}:${content}:${ts}`;
      if (seenRef.current.has(sig)) return;
      seenRef.current.add(sig);
      const agent = agents.find((a) => a.id === agentId);
      const id = `${agentId}-${ts}-${++eventIdRef.current}`;
      const buf = bufRef.current;
      buf.push({
        id,
        agent_id: agentId,
        agent_name: agent?.name ?? agentId,
        agent_color: agent?.color,
        timestamp: ts,
        event_type: eventType,
        content,
      });
      while (buf.length > MAX_EVENTS) {
        const evicted = buf.shift();
        if (evicted) {
          seenRef.current.delete(
            `${evicted.agent_id}:${evicted.event_type}:${evicted.content}:${evicted.timestamp}`
          );
        }
      }
      scheduleFlush();
    },
    [agents, scheduleFlush],
  );

  const isActive = planStatus === "active";
  const hasActivity = planStatus !== "draft";

  useEffect(() => {
    if (!token || !hasActivity) {
      setConnected(false);
      return;
    }
    let es: EventSource | null = null;
    api.auth.streamToken().then((streamToken) => {
      const base = getApiBase();
      const url = `${base}/api/plans/${planId}/logs?token=${encodeURIComponent(streamToken)}`;
      es = new EventSource(url);
      es.onopen = () => setConnected(true);
      es.addEventListener("ping", () => setConnected(true));
      es.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          addEvent(d);
        } catch {
          addEvent({ content: e.data });
        }
      };
      es.onerror = () => {
        setConnected(false);
        es?.close();
      };
    }).catch(() => setConnected(false));
    return () => {
      setConnected(false);
      es?.close();
      if (flushRef.current) cancelAnimationFrame(flushRef.current);
    };
  }, [token, planId, hasActivity, addEvent]);

  const filteredEvents = (() => {
    const allowed = new Set(BASE_LABELS);
    if (showTool) allowed.add("Tool");
    if (showMessage) allowed.add("Message");
    return events
      .filter((e) => allowed.has(getEventDisplay(e.event_type).label))
      .slice(-DISPLAY_LIMIT)
      .reverse();
  })();

  return (
    <div className="flex h-full flex-col -m-4">
      <div className="flex-1 flex flex-col min-h-0 min-w-0 overflow-hidden">
        {/* Filter bar */}
        <div className="flex items-center gap-3 border-b border-claude-border px-3 py-2 shrink-0">
          <span className="text-[11px] font-medium text-claude-text-muted">Show:</span>
          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showTool}
              onChange={(e) => setShowTool(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-claude-border text-claude-accent accent-claude-accent"
            />
            <span className={`text-[11px] font-medium ${showTool ? "text-claude-text-primary" : "text-claude-text-muted"}`}>Tools</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showMessage}
              onChange={(e) => setShowMessage(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-claude-border text-claude-accent accent-claude-accent"
            />
            <span className={`text-[11px] font-medium ${showMessage ? "text-claude-text-primary" : "text-claude-text-muted"}`}>Messages</span>
          </label>
          <span className="ml-auto flex items-center gap-2 text-[10px] text-claude-text-muted tabular-nums">
            {hasActivity && (
              <span className={`flex items-center gap-1 ${connected ? (isActive ? "text-green-600" : "text-blue-500") : "text-amber-500"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${connected ? (isActive ? "bg-green-500" : "bg-blue-400") : "bg-amber-400 animate-pulse"}`} />
                {connected ? (isActive ? "Live" : "History") : "Connecting…"}
              </span>
            )}
            {filteredEvents.length} event{filteredEvents.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Timeline content */}
        <div className="flex-1 overflow-y-auto min-h-0 px-3 py-2">
          {filteredEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <svg className="h-7 w-7 text-claude-border-strong mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-xs text-claude-text-muted">
                {planStatus === "draft"
                  ? "Plan is in draft. Assign agents and tasks, then activate to start."
                  : planStatus === "paused"
                    ? "Plan is paused. Activity history will appear once agents start working."
                    : planStatus === "completed"
                      ? "Plan completed. Activity history is shown above."
                      : connected
                        ? "Agents are active — activity will appear here as they work."
                        : "Connecting to activity stream…"}
              </p>
            </div>
          ) : (
            <div className="relative">
              <div className="absolute left-4 top-0 bottom-0 w-px bg-claude-border" />
              {filteredEvents.map((ev) => {
                const meta = getEventDisplay(ev.event_type);
                return meta.isLifecycle
                  ? <TimelineLifecycleEvent key={ev.id} ev={ev} meta={meta} />
                  : <TimelineContentEvent key={ev.id} ev={ev} meta={meta} />;
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function taskStatusColor(columnId: string): string {
  switch (columnId) {
    case "col-done":
      return "bg-green-100 text-green-800";
    case "col-in-progress":
      return "bg-blue-100 text-blue-800";
    case "col-blocked":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-claude-surface text-claude-text-secondary";
  }
}

function TaskCard({
  task,
  planId,
  agentName,
  statusLabel,
  columnId,
  onView,
  onEdit,
}: {
  task: PlanTaskType;
  planId: string;
  agentName?: string;
  statusLabel: string;
  columnId: string;
  onView: (task: PlanTaskType) => void;
  onEdit: (task: PlanTaskType) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const didDragRef = useRef(false);
  const deleteTask = useDeleteTask(planId);

  function handleDragStart(e: React.DragEvent) {
    didDragRef.current = true;
    setDragging(true);
    e.dataTransfer.setData("application/json", JSON.stringify({ taskId: task.id, columnId: task.column_id }));
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDragEnd() {
    setDragging(false);
  }

  function handleClick() {
    if (didDragRef.current) {
      didDragRef.current = false;
      return;
    }
    onView(task);
  }

  return (
    <div
      id={`task-${task.id}`}
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onClick={handleClick}
      className={`min-w-0 w-full rounded-lg border border-claude-border bg-white p-3 shadow-sm transition-shadow ${
        dragging ? "opacity-60" : "hover:shadow-md hover:border-claude-accent/40"
      } cursor-pointer active:cursor-grabbing`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="min-w-0 flex-1 text-sm font-semibold text-claude-text-primary">{task.title || "Untitled"}</p>
          <div className="flex shrink-0 items-center gap-0.5">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onEdit(task);
              }}
              className="rounded p-0.5 text-claude-text-muted hover:bg-claude-surface hover:text-claude-accent transition-colors"
              title="Edit task"
            >
              <PencilIcon className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                deleteTask.mutate(task.id);
              }}
              disabled={deleteTask.isPending}
              className="rounded p-0.5 text-claude-text-muted hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-50"
              title="Delete task"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        {task.description ? (
          <p className="mt-1 line-clamp-3 text-xs text-claude-text-muted">{task.description}</p>
        ) : null}
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-claude-border/60 pt-2 text-[11px] text-claude-text-muted">
          <span className="flex items-center gap-1">
            <PeopleIcon className="h-3 w-3 shrink-0" />
            {agentName ?? "Unassigned"}
          </span>
          <span
            className={`inline-flex rounded-full px-1.5 py-0.5 font-medium ${taskStatusColor(columnId)}`}
          >
            {statusLabel}
          </span>
        </div>
      </div>
    </div>
  );
}

function KanbanColumn({
  column,
  planId,
  tasks,
  agents,
  onDrop,
  onOpenCreateTask,
  onViewTask,
  onEditTask,
}: {
  column: PlanColumnType;
  planId: string;
  tasks: PlanTaskType[];
  agents: { id: string; name: string }[];
  onDrop: (columnId: string, taskId: string) => void;
  onOpenCreateTask: (columnId: string, columnTitle: string) => void;
  onViewTask: (task: PlanTaskType) => void;
  onEditTask: (task: PlanTaskType) => void;
}) {
  const [over, setOver] = useState(false);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setOver(true);
  }

  function handleDragLeave() {
    setOver(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setOver(false);
    try {
      const data = JSON.parse(e.dataTransfer.getData("application/json") || "{}");
      if (data.taskId && data.columnId !== column.id) {
        onDrop(column.id, data.taskId);
      }
    } catch {
      // ignore
    }
  }

  const agentMap = Object.fromEntries(agents.map((a) => [a.id, a.name]));

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`flex min-w-0 flex-1 flex-col border-r border-claude-border last:border-r-0 transition-colors ${
        over ? "bg-claude-accent/5" : ""
      }`}
    >
      <h3 className="shrink-0 border-b border-claude-border px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-claude-text-muted">
        {column.title}
      </h3>
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-3">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            planId={planId}
            agentName={task.agent_id ? agentMap[task.agent_id] : undefined}
            statusLabel={column.title}
            columnId={column.id}
            onView={onViewTask}
            onEdit={onEditTask}
          />
        ))}
      </div>
      <button
        type="button"
        onClick={() => onOpenCreateTask(column.id, column.title)}
        className="shrink-0 border-t border-claude-border py-2 text-xs text-claude-text-muted hover:bg-claude-surface hover:text-claude-accent transition-colors"
      >
        <span className="text-base">+</span> Add task
      </button>
    </div>
  );
}

function ManageAgentsModal({
  open,
  onClose,
  agents,
  assignedIds,
  onAssign,
  onRemove,
}: {
  open: boolean;
  onClose: () => void;
  agents: { id: string; name: string; status: string }[];
  assignedIds: string[];
  onAssign: (agentId: string) => void;
  onRemove: (agentId: string) => void;
}) {
  return (
    <Modal open={open} onClose={onClose} title="Manage Agents" icon={<PeopleIcon className="h-4 w-4" />} size="lg">
      <p className="mb-3 text-xs text-claude-text-muted">
        Agents run separately. Assign agents so they can see and work on this plan; plan status is visible to agents via PlanTool.
      </p>
      <div className="space-y-2 max-h-[50vh] overflow-y-auto">
        {agents.map((agent) => {
          const assigned = assignedIds.includes(agent.id);
          return (
            <div
              key={agent.id}
              className="flex items-center justify-between rounded-lg border border-claude-border px-3 py-2"
            >
              <span className="text-sm font-medium text-claude-text-primary">{agent.name}</span>
              {assigned ? (
                <button
                  type="button"
                  onClick={() => onRemove(agent.id)}
                  className="text-[11px] font-medium text-red-600 hover:underline"
                >
                  Remove
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => onAssign(agent.id)}
                  className="text-[11px] font-medium text-claude-accent hover:underline"
                >
                  Assign
                </button>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg bg-claude-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-claude-accent-hover"
        >
          Done
        </button>
      </div>
    </Modal>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(contentType: string): string {
  if (contentType.startsWith("image/")) return "image";
  if (contentType.startsWith("text/") || contentType.includes("json") || contentType.includes("xml")) return "text";
  if (contentType.includes("pdf")) return "pdf";
  if (contentType.includes("zip") || contentType.includes("tar") || contentType.includes("gzip")) return "archive";
  return "file";
}

function FileTypeIcon({ type, className }: { type: string; className?: string }) {
  const c = className ?? "h-4 w-4";
  if (type === "image") {
    return (
      <svg className={c} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
      </svg>
    );
  }
  if (type === "text") {
    return (
      <svg className={c} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    );
  }
  return (
    <svg className={c} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

/* ── Plan Artifact Section ─────────────────────────────────────────────────────── */

function ArtifactFolderIcon({ className }: { className?: string }) {
  return (
    <svg className={className ?? "h-3 w-3"} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
    </svg>
  );
}

function isMarkdownArtifact(a: PlanArtifact): boolean {
  if (a.content_type && (a.content_type === "text/markdown" || a.content_type === "text/x-markdown")) return true;
  if (a.name && a.name.toLowerCase().endsWith(".md")) return true;
  return false;
}

function isTextArtifact(a: PlanArtifact): boolean {
  if (!a.content_type) return false;
  return (
    a.content_type.startsWith("text/") ||
    a.content_type === "application/json" ||
    a.content_type === "application/xml"
  );
}

function ArtifactSection({
  planId,
  artifacts,
  tasks,
}: {
  planId: string;
  artifacts: PlanArtifact[];
  tasks: PlanTaskType[];
}) {
  const [dragOver, setDragOver] = useState(false);
  const [viewArtifact, setViewArtifact] = useState<PlanArtifact | null>(null);
  const [viewArtifactContent, setViewArtifactContent] = useState<string | null>(null);
  const [viewArtifactLoading, setViewArtifactLoading] = useState(false);
  const [renameArtifact, setRenameArtifact] = useState<PlanArtifact | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [moveArtifact, setMoveArtifact] = useState<PlanArtifact | null>(null);
  const [moveTaskId, setMoveTaskId] = useState("");
  const [draggingArtifact, setDraggingArtifact] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadArtifact = useUploadArtifact(planId);
  const deleteArtifact = useDeleteArtifact(planId);
  const renameArtifactMutation = useRenameArtifact(planId);
  const moveArtifactMutation = useMoveArtifact(planId);

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      Array.from(files).forEach((file) => {
        uploadArtifact.mutate(file);
      });
    },
    [uploadArtifact],
  );

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types.includes("Files")) {
      e.dataTransfer.dropEffect = "copy";
      setDragOver(true);
    } else if (e.dataTransfer.types.includes("application/x-artifact")) {
      e.dataTransfer.dropEffect = "move";
      setDragOver(true);
    }
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    } else if (e.dataTransfer.types.includes("application/x-artifact")) {
      const artifactId = e.dataTransfer.getData("application/x-artifact");
      if (artifactId) {
        moveArtifactMutation.mutate({ artifactId, taskId: "" });
      }
    }
  }

  function handleArtifactDragStart(e: React.DragEvent, artifact: PlanArtifact) {
    setDraggingArtifact(artifact.id);
    e.dataTransfer.setData("application/x-artifact", artifact.id);
    e.dataTransfer.effectAllowed = "move";
  }

  function handleArtifactDragEnd() {
    setDraggingArtifact(null);
  }

  async function openViewArtifact(a: PlanArtifact) {
    setViewArtifact(a);
    if (a.file_path && (isMarkdownArtifact(a) || isTextArtifact(a))) {
      setViewArtifactContent(null);
      setViewArtifactLoading(true);
      try {
        const url = api.plans.downloadArtifactUrl(planId, a.id);
        const token = localStorage.getItem("token");
        const res = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) {
          const text = await res.text();
          setViewArtifactContent(text);
        } else {
          setViewArtifactContent(null);
        }
      } catch {
        setViewArtifactContent(null);
      } finally {
        setViewArtifactLoading(false);
      }
    } else {
      setViewArtifactContent(a.content ?? null);
      setViewArtifactLoading(false);
    }
  }

  async function handleDownload(a: PlanArtifact) {
    if (!a.file_path && !a.content) return;
    const url = api.plans.downloadArtifactUrl(planId, a.id);
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`Download failed: ${res.status}`);
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = a.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch {
      window.open(url, "_blank");
    }
  }

  function openRenameModal(a: PlanArtifact) {
    setRenameArtifact(a);
    setRenameValue(a.name);
  }

  function handleRenameSubmit() {
    if (!renameArtifact || !renameValue.trim()) return;
    if (renameValue.includes("/") || renameValue.includes("..")) return;
    renameArtifactMutation.mutate(
      { artifactId: renameArtifact.id, newName: renameValue.trim() },
      { onSuccess: () => setRenameArtifact(null) },
    );
  }

  function openMoveModal(a: PlanArtifact) {
    setMoveArtifact(a);
    setMoveTaskId(a.task_id || "");
  }

  function handleMoveSubmit() {
    if (!moveArtifact) return;
    moveArtifactMutation.mutate(
      { artifactId: moveArtifact.id, taskId: moveTaskId },
      { onSuccess: () => setMoveArtifact(null) },
    );
  }

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`rounded-lg transition-colors ${dragOver ? "bg-claude-accent/5 ring-2 ring-claude-accent/30" : ""}`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-claude-text-primary">Files</p>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadArtifact.isPending}
        >
          {uploadArtifact.isPending ? "Uploading…" : "Upload"}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFiles(e.target.files);
              e.target.value = "";
            }
          }}
        />
      </div>

      {uploadArtifact.isError && (
        <p className="mb-1.5 text-[11px] text-red-600">{uploadArtifact.error?.message ?? "Upload failed"}</p>
      )}

      {artifacts.length > 0 ? (
        <ul className="space-y-px">
          {artifacts.map((a) => {
            const isFile = !!a.file_path;
            const fType = fileIcon(a.content_type);
            const canPreviewFile = isFile && (isMarkdownArtifact(a) || isTextArtifact(a));
            const canPreview = (!isFile && !!a.content) || canPreviewFile;
            const isDragging = draggingArtifact === a.id;
            return (
              <li
                key={a.id}
                draggable
                onDragStart={(e) => handleArtifactDragStart(e, a)}
                onDragEnd={handleArtifactDragEnd}
                role={canPreview ? "button" : undefined}
                tabIndex={canPreview ? 0 : undefined}
                onClick={canPreview ? () => openViewArtifact(a) : undefined}
                onKeyDown={canPreview ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openViewArtifact(a); } } : undefined}
                className={`group flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-claude-surface/60 ${canPreview ? "cursor-pointer" : "cursor-grab"} ${isDragging ? "opacity-50" : ""}`}
              >
                <span className="shrink-0 text-claude-text-muted">
                  <FileTypeIcon type={fType} className="h-3.5 w-3.5" />
                </span>
                {isFile && !canPreviewFile ? (
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); handleDownload(a); }}
                    className="min-w-0 flex-1 truncate text-left text-xs font-medium text-claude-accent hover:underline"
                    title={`Download ${a.name}`}
                  >
                    {a.name}
                  </button>
                ) : (
                  <span className="min-w-0 flex-1 truncate text-xs text-claude-text-primary">{a.name}</span>
                )}
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); openRenameModal(a); }}
                  className="shrink-0 rounded p-0.5 text-claude-text-muted opacity-0 transition-all hover:bg-claude-surface hover:text-claude-accent group-hover:opacity-100"
                  title="Rename"
                >
                  <PencilIcon className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); openMoveModal(a); }}
                  className="shrink-0 rounded p-0.5 text-claude-text-muted opacity-0 transition-all hover:bg-claude-surface hover:text-claude-accent group-hover:opacity-100"
                  title="Move to task"
                >
                  <ArtifactFolderIcon className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); deleteArtifact.mutate(a.id); }}
                  disabled={deleteArtifact.isPending}
                  className="shrink-0 rounded p-0.5 text-claude-text-muted opacity-0 transition-all hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 disabled:opacity-50"
                  title="Delete"
                >
                  <TrashIcon className="h-3 w-3" />
                </button>
                <span className="shrink-0 text-[10px] text-claude-text-muted tabular-nums">
                  {a.size ? formatFileSize(a.size) : ""}
                </span>
                <span className="shrink-0 text-[10px] text-claude-text-muted tabular-nums">
                  {a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}
                </span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="py-2 text-center text-[11px] text-claude-text-muted">No files yet. Drag and drop or upload files to share with all agents.</p>
      )}

      {/* Rename Modal */}
      <Modal open={!!renameArtifact} onClose={() => setRenameArtifact(null)} title="Rename File" size="default">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleRenameSubmit();
          }}
        >
          <input
            type="text"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            placeholder="New name"
            autoFocus
            className="mb-4 w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent"
          />
          {renameArtifactMutation.isError && (
            <p className="mb-2 text-[11px] text-red-600">{renameArtifactMutation.error?.message ?? "Rename failed"}</p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" type="button" onClick={() => setRenameArtifact(null)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={renameArtifactMutation.isPending || !renameValue.trim()}>
              {renameArtifactMutation.isPending ? "Renaming…" : "Rename"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Move Modal */}
      <Modal open={!!moveArtifact} onClose={() => setMoveArtifact(null)} title="Move to Task" size="default">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleMoveSubmit();
          }}
        >
          <p className="mb-2 text-xs text-claude-text-muted">
            Select a task to associate this file with, or choose "No task" to keep it as a general plan file.
          </p>
          <select
            value={moveTaskId}
            onChange={(e) => setMoveTaskId(e.target.value)}
            className="mb-4 w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm text-claude-text-primary focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent"
          >
            <option value="">(No task - general plan file)</option>
            {tasks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title || `Task ${t.id.slice(0, 8)}`}
              </option>
            ))}
          </select>
          {moveArtifactMutation.isError && (
            <p className="mb-2 text-[11px] text-red-600">{moveArtifactMutation.error?.message ?? "Move failed"}</p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" type="button" onClick={() => setMoveArtifact(null)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={moveArtifactMutation.isPending}>
              {moveArtifactMutation.isPending ? "Moving…" : "Move"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* View Modal */}
      <Modal
        open={!!viewArtifact}
        onClose={() => { setViewArtifact(null); setViewArtifactContent(null); }}
        title={viewArtifact?.name ?? "File"}
        size="xl"
      >
        {viewArtifact && (
          <div>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {viewArtifact.content_type && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-claude-accent/10 px-2.5 py-1 text-[11px] font-medium text-claude-accent">
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>
                  {viewArtifact.content_type}
                </span>
              )}
              {viewArtifact.size ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-claude-surface px-2.5 py-1 text-[11px] font-medium text-claude-text-secondary">
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75" /></svg>
                  {formatFileSize(viewArtifact.size)}
                </span>
              ) : null}
              {viewArtifact.created_at && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-claude-surface px-2.5 py-1 text-[11px] font-medium text-claude-text-secondary">
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                  {new Date(viewArtifact.created_at).toLocaleString()}
                </span>
              )}
              {viewArtifact.task_id && (
                <button
                  type="button"
                  onClick={() => {
                    setViewArtifact(null);
                    setViewArtifactContent(null);
                    setTimeout(() => {
                      const el = document.getElementById(`task-${viewArtifact.task_id}`);
                      if (el) {
                        el.scrollIntoView({ behavior: "smooth", block: "center" });
                        el.classList.add("ring-2", "ring-claude-accent", "ring-offset-2");
                        setTimeout(() => el.classList.remove("ring-2", "ring-claude-accent", "ring-offset-2"), 2000);
                      }
                    }, 200);
                  }}
                  className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-medium text-blue-700 transition-colors hover:bg-blue-100"
                >
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m9.86-2.54a4.5 4.5 0 0 0-1.242-7.244l-4.5-4.5a4.5 4.5 0 0 0-6.364 6.364L4.343 8.69" /></svg>
                  Task {viewArtifact.task_id.slice(0, 8)}…
                </button>
              )}
              {viewArtifact.file_path && (
                <button
                  type="button"
                  onClick={() => handleDownload(viewArtifact)}
                  className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-claude-surface px-2.5 py-1 text-[11px] font-medium text-claude-text-secondary transition-colors hover:bg-claude-border hover:text-claude-text-primary"
                >
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
                  Download
                </button>
              )}
            </div>
            {viewArtifactLoading ? (
              <div className="flex items-center justify-center py-10 text-claude-text-muted text-sm">
                <svg className="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>
                Loading…
              </div>
            ) : isMarkdownArtifact(viewArtifact) ? (
              <article
                className="prose prose-sm max-w-none text-claude-text-primary"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(viewArtifactContent ?? "") }}
              />
            ) : (viewArtifactContent != null) ? (
              <pre className="overflow-auto rounded-lg bg-claude-surface p-4 text-xs text-claude-text-primary whitespace-pre-wrap break-words">
                {viewArtifactContent}
              </pre>
            ) : null}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default function PlanBoard() {
  const { planId } = useParams<{ planId: string }>();
  const { data: plan, isLoading } = usePlan(planId);
  const { data: claws = [] } = useClaws();
  const [agentsModalOpen, setAgentsModalOpen] = useState(false);
  const [createTaskColumn, setCreateTaskColumn] = useState<{ columnId: string; columnTitle: string } | null>(null);
  const [viewTask, setViewTask] = useState<PlanTaskType | null>(null);
  const [editTask, setEditTask] = useState<PlanTaskType | null>(null);
  type RunPanelTab = "general" | "timeline";
  const [runPanelTab, setRunPanelTab] = useState<RunPanelTab>("general");
  const updateTask = useUpdateTask(planId ?? "");
  const assignAgent = useAssignAgent(planId ?? "");
  const removeAgent = useRemoveAgent(planId ?? "");
  const activatePlan = useActivatePlan();
  const deactivatePlan = useDeactivatePlan();
  const completePlan = useCompletePlan();
  const { data: artifacts = [] } = usePlanArtifacts(planId ?? undefined);

  const [splitPct, setSplitPct] = useState(65);
  const splitContainerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  useEffect(() => {
    function onMouseMove(e: MouseEvent) {
      if (!draggingRef.current || !splitContainerRef.current) return;
      const rect = splitContainerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitPct(Math.min(85, Math.max(30, pct)));
    }
    function onMouseUp() {
      if (draggingRef.current) {
        draggingRef.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    }
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);


  function startDrag(e: React.MouseEvent) {
    e.preventDefault();
    draggingRef.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }

  function handleDrop(targetColumnId: string, taskId: string) {
    if (!planId) return;
    const task = plan?.tasks.find((t) => t.id === taskId);
    if (!task) return;
    const tasksInColumn = (plan?.tasks ?? []).filter((t) => t.column_id === targetColumnId);
    const maxPos = Math.max(-1, ...tasksInColumn.map((t) => t.position));
    updateTask.mutate({ taskId, data: { column_id: targetColumnId, position: maxPos + 1 } });
  }

  if (!planId) {
    return (
      <PageContainer>
        <p className="text-claude-text-muted">Missing plan ID.</p>
      </PageContainer>
    );
  }

  if (isLoading || !plan) {
    return (
      <PageContainer>
        <p className="text-claude-text-muted">{isLoading ? "Loading…" : "Plan not found."}</p>
      </PageContainer>
    );
  }

  const unassignedCount = (plan.tasks ?? []).filter((t) => !t.agent_id).length;

  const activateError = activatePlan.error as (Error & { detail?: { agents?: string[]; message?: string } }) | null;
  const agentsNotRunning = activateError?.detail?.agents ?? [];

  return (
    <PageContainer wide className="flex flex-col">
      <div className="mb-4 shrink-0 flex items-center gap-2">
        <Link
          to="/plans"
          className="text-sm text-claude-text-muted hover:text-claude-accent transition-colors"
        >
          Plans
        </Link>
        <span className="text-claude-text-muted">/</span>
        <span className="text-sm font-medium text-claude-text-primary">{plan.name}</span>
      </div>
      {agentsNotRunning.length > 0 && (
        <div className="mb-3 rounded-lg border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-sm text-amber-700">
          <p className="font-medium">Activation failed: start these agents first.</p>
          <p className="mt-1 text-claude-text-muted">
            {agentsNotRunning.map((id) => (
              <Link key={id} to={`/agents/${id}`} className="text-claude-accent hover:underline mr-2">
                {claws.find((c) => c.id === id)?.name ?? id}
              </Link>
            ))}
          </p>
          <button
            type="button"
            onClick={() => activatePlan.reset()}
            className="mt-2 text-xs text-claude-text-muted hover:text-claude-text-primary"
          >
            Dismiss
          </button>
        </div>
      )}
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            {plan.name}
            <Badge status={plan.status} />
          </span>
        }
        description={plan.description || undefined}
        icon={<PlanIcon className="h-5 w-5" />}
        action={
          <div className="flex items-center gap-2">
            {plan.status === "draft" && (
              <>
                {unassignedCount > 0 && (
                  <span className="text-xs text-amber-600 font-medium">
                    {unassignedCount} unassigned task{unassignedCount !== 1 ? "s" : ""}
                  </span>
                )}
                <Button
                  onClick={() => activatePlan.mutate(planId)}
                  disabled={activatePlan.isPending}
                >
                  <PlayIcon className="mr-1.5 h-4 w-4" />
                  Activate
                </Button>
              </>
            )}
            {plan.status === "active" && (
              <>
                <Button
                  variant="danger"
                  onClick={() => deactivatePlan.mutate(planId)}
                  disabled={deactivatePlan.isPending}
                >
                  <StopIcon className="mr-1.5 h-4 w-4" />
                  Pause
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => completePlan.mutate(planId)}
                  disabled={completePlan.isPending}
                >
                  <CheckIcon className="mr-1.5 h-4 w-4" />
                  Mark Completed
                </Button>
              </>
            )}
            {plan.status === "paused" && (
              <>
                <Button
                  onClick={() => activatePlan.mutate(planId)}
                  disabled={activatePlan.isPending}
                >
                  <PlayIcon className="mr-1.5 h-4 w-4" />
                  Resume
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => completePlan.mutate(planId)}
                  disabled={completePlan.isPending}
                >
                  <CheckIcon className="mr-1.5 h-4 w-4" />
                  Mark Completed
                </Button>
              </>
            )}
          </div>
        }
      />

      <div ref={splitContainerRef} className="flex h-[calc(100vh-14rem)]">
        {/* Left: Kanban */}
        <div className="flex min-w-0 flex-col rounded-xl border border-claude-border bg-claude-surface/30 overflow-hidden" style={{ width: `${splitPct}%` }}>
          <div className="flex flex-1 overflow-auto">
            {(plan.columns ?? []).sort((a, b) => a.position - b.position).map((col) => (
              <KanbanColumn
                key={col.id}
                column={col}
                planId={planId}
                tasks={(plan.tasks ?? []).filter((t) => t.column_id === col.id).sort((a, b) => a.position - b.position)}
                agents={claws.map((c) => ({ id: c.id, name: c.name }))}
                onDrop={handleDrop}
                onOpenCreateTask={(columnId, columnTitle) => setCreateTaskColumn({ columnId, columnTitle })}
                onViewTask={setViewTask}
                onEditTask={setEditTask}
              />
            ))}
          </div>
        </div>

        {/* Resize handle */}
        <div
          onMouseDown={startDrag}
          className="group flex w-4 shrink-0 cursor-col-resize items-center justify-center"
        >
          <div className="h-8 w-1 rounded-full bg-claude-border transition-colors group-hover:bg-claude-accent group-active:bg-claude-accent" />
        </div>

        {/* Right: General | Timeline tab + content */}
        <div className="flex min-w-0 flex-1 flex-col rounded-xl border border-claude-border bg-white overflow-hidden">
          <div className="flex shrink-0 border-b border-claude-border">
            <button
              type="button"
              onClick={() => setRunPanelTab("general")}
              className={`px-4 py-2.5 text-sm font-medium transition-colors ${
                runPanelTab === "general"
                  ? "border-b-2 border-claude-accent text-claude-accent -mb-px"
                  : "text-claude-text-muted hover:text-claude-text-primary"
              }`}
            >
              General
            </button>
            <button
              type="button"
              onClick={() => setRunPanelTab("timeline")}
              className={`px-4 py-2.5 text-sm font-medium transition-colors ${
                runPanelTab === "timeline"
                  ? "border-b-2 border-claude-accent text-claude-accent -mb-px"
                  : "text-claude-text-muted hover:text-claude-text-primary"
              }`}
            >
              Timeline
            </button>
          </div>
          <div className={`flex-1 min-h-0 ${runPanelTab === "timeline" ? "overflow-hidden p-4" : "overflow-auto p-4 space-y-4"}`}>
            {runPanelTab === "general" && (
              <>
                {plan.description && (
                  <div>
                    <p className="mb-1 text-sm font-semibold text-claude-text-primary">Description</p>
                    <p className="text-xs text-claude-text-primary">{plan.description}</p>
                  </div>
                )}
                <div>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="flex items-center gap-1.5 text-sm font-semibold text-claude-text-primary"><ClawIcon className="h-4 w-4" />Claws</p>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setAgentsModalOpen(true)}
                    >
                      Manage ({plan.agent_ids?.length ?? 0})
                    </Button>
                  </div>
                  {plan.agent_ids?.length > 0 ? (
                    <ul className="space-y-1.5">
                      {plan.agent_ids.map((id: string) => {
                        const claw = claws.find((c) => c.id === id);
                        const taskCount = (plan.tasks ?? []).filter((t) => t.agent_id === id).length;
                        return (
                          <li key={id} className="flex items-center gap-2 text-sm text-claude-text-primary">
                            <span className="h-2 w-2 shrink-0 rounded-full bg-current opacity-60" style={{ color: claw?.color ?? "var(--claude-text-muted)" }} />
                            <Link to={`/agents/${id}`} className="hover:text-claude-accent hover:underline transition-colors">
                              {claw?.name ?? id}
                            </Link>
                            <span className="text-[11px] text-claude-text-muted">
                              {taskCount === 0 ? "(no tasks)" : `${taskCount} task${taskCount !== 1 ? "s" : ""}`}
                            </span>
                            {claw?.status != null && (
                              <Badge status={claw.status} className="text-[10px]" />
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p className="text-xs text-claude-text-muted">No agents assigned. Use "Manage agents" to assign.</p>
                  )}
                </div>
                <ArtifactSection planId={planId} artifacts={artifacts} tasks={plan.tasks ?? []} />
              </>
            )}
            {runPanelTab === "timeline" && (
              <PlanTimeline
                planId={planId}
                agents={claws.filter((c) => (plan.agent_ids ?? []).includes(c.id))}
                planStatus={plan.status}
              />
            )}
          </div>
        </div>
      </div>

      {createTaskColumn && (
        <CreateTaskModal
          open={!!createTaskColumn}
          onClose={() => setCreateTaskColumn(null)}
          planId={planId}
          columnId={createTaskColumn.columnId}
          columnTitle={createTaskColumn.columnTitle}
          agents={claws.filter((c) => plan.agent_ids?.includes(c.id)).map((c) => ({ id: c.id, name: c.name }))}
        />
      )}

      <TaskDetailModal
        open={!!viewTask}
        onClose={() => setViewTask(null)}
        onEdit={() => {
          const t = viewTask;
          setViewTask(null);
          setEditTask(t);
        }}
        planId={planId}
        task={viewTask}
        columns={plan.columns ?? []}
        agents={claws.map((c) => ({ id: c.id, name: c.name }))}
      />

      <EditTaskModal
        open={!!editTask}
        onClose={() => setEditTask(null)}
        planId={planId}
        task={editTask}
        columns={plan.columns ?? []}
        agents={(() => {
          const planAgentIds = new Set(plan.agent_ids ?? []);
          const list = claws.filter((c) => planAgentIds.has(c.id)).map((c) => ({ id: c.id, name: c.name }));
          if (editTask?.agent_id && !planAgentIds.has(editTask.agent_id)) {
            const current = claws.find((c) => c.id === editTask.agent_id);
            if (current) list.push({ id: current.id, name: current.name });
          }
          return list;
        })()}
      />

      <ManageAgentsModal
        open={agentsModalOpen}
        onClose={() => setAgentsModalOpen(false)}
        agents={claws}
        assignedIds={plan.agent_ids ?? []}
        onAssign={(agentId) => assignAgent.mutate(agentId)}
        onRemove={(agentId) => removeAgent.mutate(agentId)}
      />

    </PageContainer>
  );
}
