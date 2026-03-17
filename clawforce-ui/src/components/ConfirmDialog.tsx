import Modal from "./Modal";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  isPending?: boolean;
  variant?: "danger" | "default";
}

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  isPending = false,
  variant = "default",
}: ConfirmDialogProps) {
  const btnClass =
    variant === "danger"
      ? "rounded-lg bg-red-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      : "rounded-lg bg-claude-accent px-4 py-1.5 text-sm font-medium text-white hover:bg-claude-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors";

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-claude-text-secondary">{message}</p>
      <div className="flex justify-end gap-2 pt-4">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg px-3 py-1.5 text-sm text-claude-text-muted hover:text-claude-text-secondary transition-colors"
        >
          Cancel
        </button>
        <button type="button" onClick={onConfirm} disabled={isPending} className={btnClass}>
          {isPending ? "Deleting…" : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
