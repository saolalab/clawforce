import { useEffect, useRef, useState } from "react";
import { api } from "../../../lib/api";
import { css, PROVIDER_DEFS } from "../constants";
import { detectProvider } from "../utils";

type FetchedModel = { id: string; name: string };

export function ModelProviderSection({
  agentId,
  model,
  savedProviders,
  onModelChange,
  onProviderKeyChange,
}: {
  agentId: string;
  model: string;
  savedProviders?: Record<string, Record<string, unknown>>;
  onModelChange: (model: string) => void;
  onProviderKeyChange: (provider: string, apiKey: string) => void;
}) {
  // Derive initial provider from current model
  const detected = detectProvider(model);
  const [selectedProvider, setSelectedProvider] = useState(detected?.field || "");

  // Sync selectedProvider when model prop changes externally (e.g. after save reloads agent)
  const prevModelRef = useRef(model);
  useEffect(() => {
    if (model !== prevModelRef.current) {
      prevModelRef.current = model;
      const newDetected = detectProvider(model);
      if (newDetected?.field && newDetected.field !== selectedProvider) {
        setSelectedProvider(newDetected.field);
      }
    }
  }, [model, selectedProvider]);

  // Load saved API key: backend stores as api_key (snake), frontend may have apiKey (camel)
  const savedKey = selectedProvider && savedProviders?.[selectedProvider]
    ? ((savedProviders[selectedProvider].apiKey ?? savedProviders[selectedProvider].api_key ?? "") as string)
    : "";
  const [apiKey, setApiKey] = useState(savedKey);

  // Sync apiKey when savedProviders refreshes (e.g. after save reloads agent data)
  const prevSavedKeyRef = useRef(savedKey);
  useEffect(() => {
    if (savedKey !== prevSavedKeyRef.current) {
      prevSavedKeyRef.current = savedKey;
      setApiKey(savedKey);
    }
  }, [savedKey]);
  const [models, setModels] = useState<FetchedModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelError, setModelError] = useState("");
  const [modelSearch, setModelSearch] = useState("");
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Non-OAuth providers that need API keys
  const providerDef = PROVIDER_DEFS.find((p) => p.field === selectedProvider);
  const needsKey = providerDef && !providerDef.oauth;

  // Close dropdown on outside click
  useEffect(() => {
    if (!modelDropdownOpen) return;
    function onClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setModelDropdownOpen(false);
        setModelSearch("");
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [modelDropdownOpen]);

  // Auto-fetch models when provider changes (static providers, or if there's a saved key)
  useEffect(() => {
    if (!selectedProvider) { setModels([]); return; }
    const isStatic = ["bedrock", "azure"].includes(selectedProvider);
    const hasSavedKey = !!(savedKey && savedKey.length > 0);
    if (isStatic || hasSavedKey) {
      setLoadingModels(true);
      setModelError("");
      // For saved (redacted) keys, pass agentId so backend uses stored key
      const keyToSend = savedKey.startsWith("***") ? "" : savedKey;
      api.providers.listModels(selectedProvider, keyToSend, keyToSend ? undefined : agentId)
        .then((r) => setModels(r.models))
        .catch(() => {})
        .finally(() => setLoadingModels(false));
    }
  }, [selectedProvider, agentId, savedKey]);

  function doFetch() {
    if (!selectedProvider) return;
    // Use explicit key if available, otherwise fall back to stored key via agentId
    const hasExplicitKey = apiKey.length > 0 && !apiKey.startsWith("***");
    if (!hasExplicitKey && !savedKey) return;
    setLoadingModels(true);
    setModelError("");
    setModels([]);
    api.providers.listModels(selectedProvider, hasExplicitKey ? apiKey : "", agentId)
      .then((r) => setModels(r.models))
      .catch((err) => {
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes("401")) {
          setModelError("Invalid API key");
        } else {
          setModelError(msg.replace(/^API \d+: /, ""));
        }
      })
      .finally(() => setLoadingModels(false));
  }

  function handleProviderChange(field: string) {
    setSelectedProvider(field);
    // Load saved API key for the new provider
    const saved = field && savedProviders?.[field]
      ? ((savedProviders[field].apiKey ?? savedProviders[field].api_key ?? "") as string)
      : "";
    setApiKey(typeof saved === "string" && !saved.startsWith("***") ? saved : "");
    setModels([]);
    setModelError("");
    setModelSearch("");
  }

  function handleModelSelect(modelId: string) {
    const fullModel = `${selectedProvider}/${modelId}`;
    // Save the provider API key into agent.providers so it's included in "Save Changes"
    if (needsKey && apiKey) {
      onProviderKeyChange(selectedProvider, apiKey);
    }
    onModelChange(fullModel);
    setModelDropdownOpen(false);
    setModelSearch("");
  }

  const currentModelDisplay = model
    ? model.includes("/") ? model.substring(model.indexOf("/") + 1) : model
    : "";

  const hasUsableKey = apiKey.length > 0 || !!(savedKey && savedKey.length > 0);

  const filteredModels = modelSearch
    ? models.filter((m) =>
      m.id.toLowerCase().includes(modelSearch.toLowerCase()) ||
      m.name.toLowerCase().includes(modelSearch.toLowerCase())
    )
    : models;

  return (
    <div className="space-y-2.5">
      {/* Row 1: Provider + API Key */}
      <div className="flex gap-4 flex-wrap items-end">
        <div className={needsKey ? "min-w-[140px]" : "flex-1 min-w-[160px]"}>
          <label className={css.label}>Provider</label>
          <select
            className={`${css.input} w-full`}
            value={selectedProvider}
            onChange={(e) => handleProviderChange(e.target.value)}
          >
            <option value="">Select a provider…</option>
            {PROVIDER_DEFS.filter((p) => !p.oauth).map((p) => (
              <option key={p.field} value={p.field}>{p.label}</option>
            ))}
          </select>
        </div>
        {selectedProvider && needsKey && (
          <div className="flex-1 min-w-[200px]">
            <label className={css.label}>API Key</label>
            <input
              className={`${css.input} w-full`}
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") doFetch(); }}
              placeholder={`${providerDef!.label} API key`}
            />
          </div>
        )}
      </div>

      {/* Row 2: Model + Fetch models */}
      {selectedProvider && (
        <div>
          <label className={css.label}>Model</label>
          {modelError && (
            <p className="text-xs text-red-500 mb-1">{modelError}</p>
          )}
          <div className="flex gap-2">
            <div ref={dropdownRef} className="relative flex-1 min-w-0">
            <button
              type="button"
              onClick={() => {
                if (models.length > 0) {
                  setModelDropdownOpen(!modelDropdownOpen);
                  setTimeout(() => searchRef.current?.focus(), 0);
                }
              }}
              disabled={models.length === 0 && !loadingModels}
              className={`${css.input} flex items-center justify-between text-left disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <span className={currentModelDisplay ? "text-claude-text-primary" : "text-claude-text-muted"}>
                {loadingModels
                  ? "Loading models…"
                  : models.length === 0
                    ? (needsKey ? (savedKey ? "Click Fetch models to load" : "Enter API key and fetch models") : "Select a provider first")
                    : currentModelDisplay || "Select a model…"}
              </span>
              <svg className="h-4 w-4 text-claude-text-muted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {modelDropdownOpen && models.length > 0 && (
              <div className="absolute z-50 mt-1 w-full rounded-xl border border-claude-border bg-white shadow-lg">
                <div className="border-b border-claude-border p-2">
                  <input
                    ref={searchRef}
                    className="w-full rounded-lg border border-claude-border bg-claude-bg px-3 py-1.5 text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none"
                    placeholder="Search models…"
                    value={modelSearch}
                    onChange={(e) => setModelSearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Escape") {
                        setModelDropdownOpen(false);
                        setModelSearch("");
                      }
                      if (e.key === "Enter" && filteredModels.length === 1) {
                        handleModelSelect(filteredModels[0].id);
                      }
                    }}
                  />
                </div>
                <div className="max-h-64 overflow-y-auto p-1">
                  {filteredModels.length === 0 && (
                    <div className="px-3 py-4 text-center text-xs text-claude-text-muted">
                      No matching models.
                    </div>
                  )}
                  {filteredModels.map((m) => {
                    const fullId = `${selectedProvider}/${m.id}`;
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => handleModelSelect(m.id)}
                        className={`flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-left text-sm transition-colors ${
                          fullId === model
                            ? "bg-claude-accent/10 text-claude-accent font-medium"
                            : "text-claude-text-secondary hover:bg-claude-surface"
                        }`}
                      >
                        <span className="font-mono text-xs truncate">{m.id}</span>
                        {m.name !== m.id && (
                          <span className="text-[10px] text-claude-text-muted ml-2 shrink-0">{m.name}</span>
                        )}
                      </button>
                    );
                  })}
                </div>
                <div className="border-t border-claude-border p-2">
                  <p className="text-[10px] text-claude-text-muted text-center">
                    {models.length} model{models.length !== 1 ? "s" : ""} available
                  </p>
                </div>
              </div>
            )}
          </div>
          {needsKey && (
            <button
              type="button"
              onClick={doFetch}
              disabled={!hasUsableKey || loadingModels}
              className={`${css.btn} shrink-0 text-claude-accent ring-1 ring-claude-accent/30 hover:bg-claude-accent/5 disabled:opacity-40 disabled:cursor-not-allowed`}
            >
              {loadingModels ? (
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : "Fetch models"}
            </button>
          )}
          </div>

          {/* Manual model input fallback */}
          <div className="mt-1.5">
            <button
              type="button"
              onClick={() => {
                const custom = prompt("Enter model ID (e.g. claude-sonnet-4-20250514):", currentModelDisplay);
                if (custom !== null && custom.trim()) {
                  const fullModel = selectedProvider ? `${selectedProvider}/${custom.trim()}` : custom.trim();
                  if (needsKey && apiKey) {
                    onProviderKeyChange(selectedProvider, apiKey);
                  }
                  onModelChange(fullModel);
                }
              }}
              className="text-[11px] text-claude-text-muted hover:text-claude-accent transition-colors"
            >
              Or enter model ID manually
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
