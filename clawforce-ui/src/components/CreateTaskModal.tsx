import { useState } from "react";
import Modal from "./Modal";
import { useAddTask } from "../lib/queries";

const css = {
  label: "mb-1 block text-xs text-claude-text-muted font-medium",
  input:
    "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
  select:
    "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm text-claude-text-primary focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
};

interface CreateTaskModalProps {
  open: boolean;
  onClose: () => void;
  planId: string;
  columnId: string;
  columnTitle: string;
  agents: { id: string; name: string }[];
}

export default function CreateTaskModal({
  open,
  onClose,
  planId,
  columnId,
  columnTitle,
  agents,
}: CreateTaskModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [agentId, setAgentId] = useState("");
  const addTask = useAddTask(planId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await addTask.mutateAsync({
      column_id: columnId,
      title: title.trim(),
      description: description.trim(),
      agent_id: agentId || undefined,
    });
    setTitle("");
    setDescription("");
    setAgentId("");
    onClose();
  }

  function handleClose() {
    setTitle("");
    setDescription("");
    setAgentId("");
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Add task"
      icon={
        <span className="flex h-4 w-4 items-center justify-center rounded bg-claude-accent/20 text-xs font-medium text-claude-accent">
          +
        </span>
      }
    >
      <p className="mb-3 text-xs text-claude-text-muted">
        Adding to <span className="font-medium text-claude-text-secondary">{columnTitle}</span>
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className={css.label}>Title</label>
          <input
            type="text"
            placeholder="e.g. Review pull request"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
            className={css.input}
          />
        </div>
        <div>
          <label className={css.label}>Description (optional)</label>
          <textarea
            placeholder="Add details or acceptance criteria…"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className={`${css.input} resize-none`}
          />
        </div>
        {agents.length > 0 && (
          <div>
            <label className={css.label}>Assign to agent (optional)</label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className={css.select}
            >
              <option value="">Unassigned</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={handleClose}
            className="rounded-lg px-3 py-1.5 text-sm text-claude-text-muted hover:text-claude-text-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!title.trim() || addTask.isPending}
            className="rounded-lg bg-claude-accent px-4 py-1.5 text-sm font-medium text-white hover:bg-claude-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {addTask.isPending ? "Adding…" : "Add task"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
