import { useEffect, useRef } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  /** Optional footer rendered fixed at bottom (does not scroll with content) */
  footer?: React.ReactNode;
  /** "default" = max-w-md, "lg" = max-w-2xl, "xl" = max-w-4xl for full-document views */
  size?: "default" | "lg" | "xl";
}

const SIZE_CLASS: Record<string, string> = {
  default: "max-w-md",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
};

export default function Modal({ open, onClose, title, icon, children, footer, size = "default" }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const maxWidthClass = SIZE_CLASS[size] ?? SIZE_CLASS.default;

  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
    >
      <div className={`w-full ${maxWidthClass} max-h-[90vh] flex flex-col rounded-xl border border-claude-border bg-white shadow-xl`}>
        <div className="flex items-center justify-between flex-shrink-0 border-b border-claude-border px-5 py-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-claude-text-primary">
            {icon && <span className="flex shrink-0 text-claude-text-muted">{icon}</span>}
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-claude-text-muted hover:text-claude-text-secondary transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex-shrink-0 border-t border-claude-border px-5 py-3 flex justify-end gap-2">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
