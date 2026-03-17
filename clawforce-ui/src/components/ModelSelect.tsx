import { useState, useRef, useEffect, useCallback } from "react";

export const MODELS = [
  // Anthropic — Claude Opus 4.6, Sonnet 4.6 (latest)
  "anthropic/claude-opus-4-6",
  "anthropic/claude-opus-4-5",
  "anthropic/claude-sonnet-4-6",
  "anthropic/claude-sonnet-4",
  "anthropic/claude-haiku-3.5",
  // OpenAI — GPT-5.2, GPT-5.1, GPT-4.1, o-series
  "openai/gpt-5.2",
  "openai/gpt-5.2-pro",
  "openai/gpt-5.2-chat-latest",
  "openai/gpt-5.1",
  "openai/gpt-5-mini",
  "openai/gpt-4.1",
  "openai/gpt-4.1-mini",
  "openai/gpt-4.1-nano",
  "openai/gpt-4o",
  "openai/gpt-4o-mini",
  "openai/gpt-4-turbo",
  "openai/o3",
  "openai/o3-mini",
  "openai/o4-mini",
  "openai/o1",
  "openai/o1-mini",
  // DeepSeek — V3.2 (chat + reasoner)
  "deepseek/deepseek-chat",
  "deepseek/deepseek-reasoner",
  // Gemini — 3.x preview, 2.5
  "gemini/gemini-3.1-pro-preview",
  "gemini/gemini-3-flash-preview",
  "gemini/gemini-2.5-pro",
  "gemini/gemini-2.5-flash",
  // Moonshot / Kimi
  "moonshot/kimi-k2.5",
  "moonshot/moonshot-v1-auto",
  // DashScope / Qwen
  "dashscope/qwen-max",
  "dashscope/qwen-plus",
  "dashscope/qwen-turbo",
  // Zhipu AI
  "zhipu/glm-4",
  "zhipu/glm-4-flash",
  // MiniMax — M2 (latest MoE)
  "minimax/MiniMax-M2",
  "minimax/MiniMax-M1",
  // Groq — Llama 4, GPT OSS, Llama 3.3
  "groq/meta-llama/llama-4-scout-17b-16e-instruct",
  "groq/openai/gpt-oss-120b",
  "groq/llama-3.3-70b-versatile",
  "groq/llama-3.1-8b-instant",
  // AWS Bedrock
  "bedrock/anthropic.claude-sonnet-4-20250514-v1:0",
  "bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
  // OpenRouter — top models by weekly usage (Mar 2026)
  "openrouter/anthropic/claude-opus-4.6",
  "openrouter/anthropic/claude-sonnet-4.6",
  "openrouter/anthropic/claude-sonnet-4.5",
  "openrouter/anthropic/claude-haiku-3.5",
  "openrouter/openai/gpt-4.1",
  "openrouter/openai/gpt-4.1-mini",
  "openrouter/openai/gpt-4o",
  "openrouter/openai/gpt-4o-mini",
  "openrouter/openai/o3",
  "openrouter/openai/o4-mini",
  "openrouter/openai/gpt-oss-120b",
  "openrouter/google/gemini-3-flash-preview",
  "openrouter/google/gemini-2.5-pro",
  "openrouter/google/gemini-2.5-flash",
  "openrouter/deepseek/deepseek-v3.2",
  "openrouter/deepseek/deepseek-r1",
  "openrouter/x-ai/grok-4.1-fast",
  "openrouter/x-ai/grok-3",
  "openrouter/moonshotai/kimi-k2.5",
  "openrouter/minimax/minimax-m2.5",
  "openrouter/meta-llama/llama-4-maverick",
  "openrouter/meta-llama/llama-4-scout",
  "openrouter/qwen/qwen3-235b-a22b",
  "openrouter/qwen/qwen3-30b-a3b",
  "openrouter/mistralai/mistral-large",
  "openrouter/mistralai/mistral-small",
  // OAuth providers
  "github_copilot/claude-sonnet-4",
  "github_copilot/gpt-4o",
];

export const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  deepseek: "DeepSeek",
  gemini: "Gemini",
  moonshot: "Moonshot / Kimi",
  dashscope: "DashScope / Qwen",
  zhipu: "Zhipu AI",
  minimax: "MiniMax",
  groq: "Groq",
  bedrock: "AWS Bedrock",
  openrouter: "OpenRouter",
  github_copilot: "GitHub Copilot",
};

export function groupModels(filter: string) {
  const groups: Record<string, string[]> = {};
  const lc = filter.toLowerCase();
  for (const m of MODELS) {
    if (lc && !m.toLowerCase().includes(lc)) continue;
    const provider = m.split("/")[0];
    (groups[provider] ??= []).push(m);
  }
  return groups;
}

const inputCls =
  "w-full rounded-lg border border-claude-border bg-claude-bg px-3 py-1.5 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors";

type Props = {
  value: string;
  onChange: (v: string) => void;
  configuredProviders?: Set<string>;
  className?: string;
};

export default function ModelSelect({ value, onChange, configuredProviders, className = "" }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const close = useCallback(() => {
    setOpen(false);
    setSearch("");
  }, []);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    }
    if (open) document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open, close]);

  const groups = groupModels(search);

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => {
          setOpen(!open);
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
        className={`${inputCls} flex items-center justify-between text-left`}
      >
        <span className={value ? "text-claude-text-primary" : "text-claude-text-muted"}>
          {value || "Select a model\u2026"}
        </span>
        <svg className="h-4 w-4 text-claude-text-muted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-xl border border-claude-border bg-white shadow-lg">
          <div className="border-b border-claude-border p-2">
            <input
              ref={inputRef}
              className="w-full rounded-lg border border-claude-border bg-claude-bg px-3 py-1.5 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none"
              placeholder="Search models\u2026"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") close();
                if (e.key === "Enter") {
                  const allFiltered = Object.values(groups).flat();
                  if (allFiltered.length === 1) {
                    onChange(allFiltered[0]);
                    close();
                  } else if (search.trim()) {
                    onChange(search.trim());
                    close();
                  }
                }
              }}
            />
          </div>
          <div className="max-h-64 overflow-y-auto p-1">
            {Object.keys(groups).length === 0 && (
              <div className="px-3 py-4 text-center text-xs text-claude-text-muted">
                No matching models.{" "}
                <button
                  type="button"
                  className="text-claude-accent hover:underline"
                  onClick={() => { onChange(search.trim()); close(); }}
                >
                  Use &ldquo;{search.trim()}&rdquo;
                </button>
              </div>
            )}
            {Object.entries(groups).map(([provider, models]) => (
              <div key={provider}>
                <div className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-claude-text-muted">
                  {PROVIDER_LABELS[provider] || provider}
                  {configuredProviders?.has(provider) && (
                    <svg className="h-3 w-3 text-green-500 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                    </svg>
                  )}
                </div>
                {models.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => { onChange(m); close(); }}
                    className={`flex w-full items-center rounded-lg px-3 py-1.5 text-left text-sm transition-colors ${
                      m === value
                        ? "bg-claude-accent/10 text-claude-accent font-medium"
                        : "text-claude-text-secondary hover:bg-claude-surface"
                    }`}
                  >
                    <span className="font-mono text-xs">{m.substring(m.indexOf("/") + 1)}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
