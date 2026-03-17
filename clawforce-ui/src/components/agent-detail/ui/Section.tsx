import React from "react";
import { css } from "../constants";

export function Section({ title, titleBadge, subtitle, children, className = "" }: { title?: string; titleBadge?: React.ReactNode; subtitle?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <div className={`${css.card} ${className}`}>
      {title && (
        <div className="flex items-center gap-2 mb-1">
          <h3 className={css.cardTitle}>{title}</h3>
          {titleBadge}
        </div>
      )}
      {subtitle && <p className="text-sm text-claude-text-secondary mb-3">{subtitle}</p>}
      {!subtitle && title && <div className="mb-2" />}
      {children}
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`${css.toggle} ${checked ? "bg-claude-accent" : "bg-claude-border-strong"}`}
      >
        <span
          className={`pointer-events-none block h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${checked ? "translate-x-4" : "translate-x-0"}`}
        />
      </button>
      {label && <span className="text-sm text-claude-text-secondary">{label}</span>}
    </label>
  );
}
