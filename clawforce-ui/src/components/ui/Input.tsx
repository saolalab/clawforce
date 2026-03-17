import { type InputHTMLAttributes, forwardRef } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
};

const Input = forwardRef<HTMLInputElement, Props>(
  ({ label, className = "", id, ...rest }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div>
        {label && (
          <label htmlFor={inputId} className="mb-1.5 block text-xs font-medium text-claude-text-muted">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`rounded-lg border border-claude-border bg-claude-bg px-3 py-2 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors ${className}`}
          {...rest}
        />
      </div>
    );
  }
);

Input.displayName = "Input";
export default Input;
