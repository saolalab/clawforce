type Props = {
  active: boolean;
  className?: string;
};

export default function StatusDot({ active, className = "" }: Props) {
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${active ? "bg-green-500" : "bg-claude-border-strong"} ${className}`}
    />
  );
}
