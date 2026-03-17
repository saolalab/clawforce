import { SECURITY_PRESETS } from "../constants";

export function SecurityPresetCard({
  preset,
  isSelected,
  onClick,
}: {
  preset: (typeof SECURITY_PRESETS)[keyof typeof SECURITY_PRESETS];
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full h-full text-left rounded-lg border-2 p-2 transition-all ${isSelected
          ? "border-claude-accent bg-claude-accent/5"
          : "border-claude-border hover:border-claude-border-strong bg-claude-bg"
        }`}
    >
      <div className="flex items-center gap-1.5 mb-0.5">
        <span className="text-xs font-medium text-claude-text-primary">{preset.name}</span>
      </div>
      <ul className="space-y-0 mb-1">
        {preset.features.map((f, i) => (
          <li key={i} className="flex items-center gap-1.5 text-[10px]">
            {"enabled" in f ? (
              <>
                {f.enabled ? (
                  <svg className="w-3 h-3 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-3 h-3 text-claude-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
                <span className={f.enabled ? "text-claude-text-secondary" : "text-claude-text-muted"}>{f.label}</span>
              </>
            ) : (
              <>
                <span className="w-3 h-3 flex items-center justify-center text-[9px] text-claude-text-muted">•</span>
                <span className="text-claude-text-muted">{f.label}:</span>
                <span className="text-claude-text-secondary">{(f as { label: string; value: string }).value}</span>
              </>
            )}
          </li>
        ))}
      </ul>
      <p className="text-[9px] text-claude-text-muted leading-snug">{preset.description}</p>
    </button>
  );
}
