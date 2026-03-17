import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  actions?: ReactNode;
  onClick?: () => void;
};

export default function ListItem({ children, actions, onClick }: Props) {
  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter" || e.key === " ") onClick(); } : undefined}
      className={`group relative flex items-center justify-between gap-3 rounded-lg border border-claude-border bg-claude-input px-3.5 py-2.5 transition-all duration-150 hover:border-claude-border-strong hover:shadow-[0_1px_4px_rgba(0,0,0,0.04)] ${onClick ? "cursor-pointer" : ""}`}
    >
      <div className="flex items-center gap-2.5 min-w-0 flex-1">{children}</div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  );
}
