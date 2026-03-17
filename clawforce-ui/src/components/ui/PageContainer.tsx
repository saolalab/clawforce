import type { HTMLAttributes, ReactNode } from "react";

type Props = HTMLAttributes<HTMLDivElement> & {
  /** "wide" stretches full width (data tables, editors, feeds). Default constrains to readable width. */
  wide?: boolean;
  children: ReactNode;
};

export default function PageContainer({
  wide = false,
  className = "",
  children,
  ...rest
}: Props) {
  return (
    <div
      className={`${wide ? "" : "mx-auto max-w-5xl"} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
