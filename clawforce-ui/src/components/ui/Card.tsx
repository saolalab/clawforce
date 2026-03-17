import type { HTMLAttributes } from "react";

type Props = HTMLAttributes<HTMLDivElement> & {
  padding?: boolean;
};

export default function Card({ padding = true, className = "", children, ...rest }: Props) {
  return (
    <div
      className={`rounded-xl border border-claude-border bg-claude-input ${padding ? "p-4" : ""} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
