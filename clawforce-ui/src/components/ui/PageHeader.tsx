import type { ReactNode } from "react";

type Props = {
  title: ReactNode;
  icon?: ReactNode;
  description?: string;
  action?: ReactNode;
};

export default function PageHeader({ title, icon, description, action }: Props) {
  return (
    <div className="mb-5">
      <div className="flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-lg font-semibold text-claude-text-primary">
          {icon && <span className="flex shrink-0 text-claude-text-muted">{icon}</span>}
          {title}
        </h1>
        {action}
      </div>
      {description && <p className="mt-1 text-sm text-claude-text-muted">{description}</p>}
    </div>
  );
}
