import { useState } from "react";
import Modal from "./Modal";
import { PlanIcon } from "./ui";
import { useCreatePlan } from "../lib/queries";

interface CreatePlanModalProps {
  open: boolean;
  onClose: () => void;
}

const css = {
  label: "mb-1 block text-xs text-claude-text-muted font-medium",
  input:
    "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
};

export default function CreatePlanModal({ open, onClose }: CreatePlanModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const createPlan = useCreatePlan();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    await createPlan.mutateAsync({ name: name.trim(), description: description.trim() });
    setName("");
    setDescription("");
    onClose();
  }

  return (
    <Modal open={open} onClose={onClose} title="Create Plan" icon={<PlanIcon className="h-4 w-4" />}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className={css.label}>Plan Name</label>
          <input
            type="text"
            placeholder="e.g. Q1 launch"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            className={css.input}
          />
        </div>
        <div>
          <label className={css.label}>Description</label>
          <textarea
            placeholder="What is this plan for?"
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
            disabled={!name.trim() || createPlan.isPending}
            className="rounded-lg bg-claude-accent px-4 py-1.5 text-sm font-medium text-white hover:bg-claude-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {createPlan.isPending ? "Creating…" : "Create Plan"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
