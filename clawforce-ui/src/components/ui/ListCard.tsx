import { Children, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  emptyMessage?: string;
};

export default function ListCard({ children, emptyMessage = "No items yet." }: Props) {
  const hasItems = Children.toArray(children).length > 0;

  return hasItems ? (
    <div className="grid gap-1.5">{children}</div>
  ) : (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-claude-border bg-claude-input/50 px-6 py-10 text-center">
      <div className="mb-1.5 h-8 w-8 rounded-full bg-claude-surface flex items-center justify-center">
        <svg className="h-4 w-4 text-claude-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
      </div>
      <p className="text-xs text-claude-text-muted">{emptyMessage}</p>
    </div>
  );
}
