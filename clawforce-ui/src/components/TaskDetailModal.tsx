import { useState } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import Modal from "./Modal";
import { PeopleIcon, PencilIcon } from "./ui";
import { usePlanArtifacts, useTaskComments, useAddComment, useDeleteComment } from "../lib/queries";
import { api } from "../lib/api";
import type {
  PlanTask as PlanTaskType,
  PlanColumn as PlanColumnType,
  PlanArtifact,
  TaskComment as TaskCommentType,
} from "../lib/types";

function renderMd(raw: string): string {
  return DOMPurify.sanitize(marked.parse(raw) as string);
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

function formatDate(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface TaskDetailModalProps {
  open: boolean;
  onClose: () => void;
  onEdit: () => void;
  planId: string;
  task: PlanTaskType | null;
  columns: PlanColumnType[];
  agents: { id: string; name: string }[];
}

export default function TaskDetailModal({
  open,
  onClose,
  onEdit,
  planId,
  task,
  columns,
  agents,
}: TaskDetailModalProps) {
  const { data: artifacts = [] } = usePlanArtifacts(
    task ? planId : undefined,
    task?.id,
  );
  const { data: comments = [] } = useTaskComments(planId, task?.id);
  const addComment = useAddComment(planId, task?.id ?? "");
  const deleteComment = useDeleteComment(planId, task?.id ?? "");
  const [viewArtifact, setViewArtifact] = useState<PlanArtifact | null>(null);
  const [viewArtifactContent, setViewArtifactContent] = useState<string | null>(null);
  const [viewArtifactLoading, setViewArtifactLoading] = useState(false);
  const [newComment, setNewComment] = useState("");

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
          setViewArtifactContent(await res.text());
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

  if (!task) return null;

  const column = columns.find((c) => c.id === task.column_id);
  const agent = agents.find((a) => a.id === task.agent_id);

  const statusColor =
    task.column_id === "col-done"
      ? "bg-green-100 text-green-800"
      : task.column_id === "col-in-progress"
        ? "bg-blue-100 text-blue-800"
        : task.column_id === "col-blocked"
          ? "bg-amber-100 text-amber-800"
          : "bg-claude-surface text-claude-text-secondary";

  return (
    <>
      <Modal
        open={open}
        onClose={onClose}
        title={task.title || "Untitled task"}
        size="xl"
        icon={
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z"
            />
          </svg>
        }
      >
        <div className="space-y-5">
          {/* Metadata pills + Edit action */}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusColor}`}
            >
              {column?.title ?? "Unknown"}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-claude-surface px-2.5 py-1 text-[11px] font-medium text-claude-text-secondary">
              <PeopleIcon className="h-3 w-3" />
              {agent?.name ?? "Unassigned"}
            </span>
            <button
              type="button"
              onClick={onEdit}
              className="ml-auto flex items-center gap-1.5 rounded-lg border border-claude-border px-3 py-1.5 text-xs font-medium text-claude-text-secondary hover:bg-claude-surface hover:text-claude-accent transition-colors"
            >
              <PencilIcon className="h-3.5 w-3.5" />
              Edit
            </button>
          </div>

          {/* Description */}
          {task.description ? (
            <div>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-claude-text-muted">
                Description
              </h4>
              <article
                className="prose prose-sm max-w-none text-claude-text-primary [&_p]:my-1 [&_ul]:my-1 [&_code]:text-xs [&_code]:bg-claude-surface [&_code]:px-1 [&_code]:rounded [&_pre]:bg-claude-surface [&_pre]:p-3 [&_pre]:rounded-lg"
                dangerouslySetInnerHTML={{
                  __html: renderMd(task.description),
                }}
              />
            </div>
          ) : (
            <p className="text-sm italic text-claude-text-muted">
              No description provided.
            </p>
          )}

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-4 rounded-lg border border-claude-border/60 bg-claude-surface/30 p-3">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-claude-text-muted">
                Created
              </p>
              <p className="mt-0.5 text-xs text-claude-text-secondary">
                {formatDate(task.created_at)}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-claude-text-muted">
                Updated
              </p>
              <p className="mt-0.5 text-xs text-claude-text-secondary">
                {formatDate(task.updated_at)}
              </p>
            </div>
          </div>

          {/* Artifacts linked to this task */}
          {artifacts.length > 0 && (
            <div>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-claude-text-muted">
                Artifacts ({artifacts.length})
              </h4>
              <ul className="space-y-1">
                {artifacts.map((a) => (
                  <li key={a.id}>
                    <button
                      type="button"
                      onClick={() => openViewArtifact(a)}
                      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs text-claude-text-primary hover:bg-claude-surface/60 transition-colors"
                    >
                      <svg
                        className="h-3.5 w-3.5 shrink-0 text-claude-text-muted"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                        />
                      </svg>
                      <span className="flex-1 truncate font-medium">
                        {a.name}
                      </span>
                      {a.created_at && (
                        <span className="shrink-0 text-[10px] text-claude-text-muted">
                          {formatDate(a.created_at)}
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Comments */}
          <div>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-claude-text-muted">
              Comments ({comments.length})
            </h4>
            <ul className="space-y-3 mb-3">
              {comments.map((c: TaskCommentType) => (
                <li
                  key={c.id}
                  className="rounded-lg border border-claude-border/60 bg-claude-surface/30 p-3"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-medium text-claude-text-primary">
                      {c.author_name}
                      <span className="ml-1.5 text-[10px] font-normal text-claude-text-muted">
                        {c.author_type === "admin" ? "Admin" : "Agent"} · {formatDate(c.created_at)}
                      </span>
                    </span>
                    <button
                      type="button"
                      onClick={() => deleteComment.mutate(c.id)}
                      disabled={deleteComment.isPending}
                      className="text-[10px] text-claude-text-muted hover:text-red-600 transition-colors"
                      title="Delete comment (admin only)"
                    >
                      Delete
                    </button>
                  </div>
                  <p className="text-sm text-claude-text-secondary whitespace-pre-wrap break-words">
                    {c.content}
                  </p>
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add a comment..."
                rows={2}
                className="flex-1 rounded-lg border border-claude-border bg-claude-surface/50 px-3 py-2 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:outline-none focus:ring-2 focus:ring-claude-accent/50"
              />
              <button
                type="button"
                onClick={() => {
                  const content = newComment.trim();
                  if (!content || addComment.isPending) return;
                  addComment.mutate(content, {
                    onSuccess: () => setNewComment(""),
                  });
                }}
                disabled={!newComment.trim() || addComment.isPending}
                className="self-stretch rounded-lg bg-claude-accent px-4 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
              >
                {addComment.isPending ? "Posting…" : "Post"}
              </button>
            </div>
          </div>
        </div>
      </Modal>

      {/* Artifact preview sub-modal */}
      <Modal
        open={!!viewArtifact}
        onClose={() => { setViewArtifact(null); setViewArtifactContent(null); }}
        title={viewArtifact?.name ?? "Artifact"}
        size="xl"
      >
        {viewArtifact && (
          <div>
            {viewArtifact.file_path && (
              <div className="mb-3 flex justify-end">
                <a
                  href={api.plans.downloadArtifactUrl(planId, viewArtifact.id)}
                  download={viewArtifact.name}
                  className="inline-flex items-center gap-1.5 rounded-full bg-claude-surface px-2.5 py-1 text-[11px] font-medium text-claude-text-secondary transition-colors hover:bg-claude-border hover:text-claude-text-primary"
                >
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
                  Download
                </a>
              </div>
            )}
            {viewArtifactLoading ? (
              <div className="flex items-center justify-center py-10 text-claude-text-muted text-sm">
                <svg className="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>
                Loading…
              </div>
            ) : isMarkdownArtifact(viewArtifact) ? (
              <article
                className="prose prose-sm max-w-none text-claude-text-primary"
                dangerouslySetInnerHTML={{ __html: renderMd(viewArtifactContent ?? "") }}
              />
            ) : (viewArtifactContent != null) ? (
              <pre className="overflow-auto rounded-lg bg-claude-surface p-4 text-xs text-claude-text-primary whitespace-pre-wrap break-words">
                {viewArtifactContent}
              </pre>
            ) : null}
          </div>
        )}
      </Modal>
    </>
  );
}
