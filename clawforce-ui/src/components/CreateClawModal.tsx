import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Modal from "./Modal";
import { ClawIcon } from "./ClawIcon";
import { useCreateClaw, useTemplates } from "../lib/queries";

interface CreateClawModalProps {
  open: boolean;
  onClose: () => void;
  initialTemplate?: string;
}

const css = {
  label: "mb-1 block text-xs text-claude-text-muted font-medium",
  input:
    "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
  select:
    "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm text-claude-text-primary focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors appearance-none cursor-pointer",
};

const CLAW_COLORS = [
  "#ef4444", "#f97316", "#f59e0b", "#eab308", "#84cc16", "#22c55e", "#10b981", "#14b8a6",
  "#06b6d4", "#0ea5e9", "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
];

function randomColor() {
  return CLAW_COLORS[Math.floor(Math.random() * CLAW_COLORS.length)];
}

export default function CreateClawModal({ open, onClose, initialTemplate }: CreateClawModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState(initialTemplate ?? "default");
  const createClaw = useCreateClaw();
  const { data: templates = [] } = useTemplates();
  const navigate = useNavigate();

  // Sync template when initialTemplate changes (e.g., when modal opens with a new template)
  useEffect(() => {
    if (initialTemplate) setTemplate(initialTemplate);
  }, [initialTemplate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const claw = await createClaw.mutateAsync({
      name: name.trim(),
      description: description.trim(),
      template: template,
      color: randomColor(),
    });
    setName("");
    setDescription("");
    setTemplate("default");
    onClose();
    navigate(`/agents/${claw.id}`);
  }

  return (
    <Modal open={open} onClose={onClose} title="Create Claw" icon={<ClawIcon className="h-4 w-4" />}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className={css.label}>Claw Name</label>
          <input
            type="text"
            placeholder="e.g. code-reviewer"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            className={css.input}
          />
        </div>
        <div>
          <label className={css.label}>Template</label>
          <div className="relative">
            <select
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              className={css.select}
            >
              {templates.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
              <svg className="h-4 w-4 text-claude-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
          <p className="mt-1 text-xs text-claude-text-muted">
            Pre-configures the claw with role-specific skills and settings
          </p>
        </div>
        <div>
          <label className={css.label}>Description</label>
          <textarea
            placeholder="What does this claw do?"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className={`${css.input} resize-none`}
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-sm text-claude-text-muted hover:text-claude-text-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim() || createClaw.isPending}
            className="rounded-lg bg-claude-accent px-4 py-1.5 text-sm font-medium text-white hover:bg-claude-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {createClaw.isPending ? "Creating…" : "Create Claw"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
