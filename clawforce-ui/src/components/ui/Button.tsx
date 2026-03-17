import { type ButtonHTMLAttributes, forwardRef } from "react";

const variants = {
  primary:
    "bg-claude-accent text-white hover:bg-claude-accent-hover",
  secondary:
    "bg-claude-surface text-claude-text-secondary ring-1 ring-claude-border hover:bg-claude-hover",
  ghost:
    "text-claude-text-tertiary hover:bg-claude-surface hover:text-claude-text-secondary",
  danger:
    "text-red-500 ring-1 ring-red-200 hover:text-red-600 hover:bg-red-50",
  success:
    "text-green-600 hover:text-green-700 hover:bg-green-50",
} as const;

const sizes = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-5 py-2.5 text-sm",
} as const;

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
};

const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = "primary", size = "md", className = "", children, ...rest }, ref) => (
    <button
      ref={ref}
      type="button"
      className={`inline-flex items-center justify-center rounded-lg font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none ${variants[variant]} ${sizes[size]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
);

Button.displayName = "Button";
export default Button;
