import { Link } from "react-router-dom";

type Crumb = { label: string; to?: string };

type Props = {
  items: Crumb[];
};

export default function Breadcrumb({ items }: Props) {
  return (
    <nav className="mb-4 flex items-center gap-2 text-sm">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-2">
          {i > 0 && <span className="text-claude-border-strong">/</span>}
          {item.to ? (
            <Link to={item.to} className="text-claude-text-muted hover:text-claude-accent hover:underline transition-colors">
              {item.label}
            </Link>
          ) : (
            <span className="text-claude-text-secondary">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
