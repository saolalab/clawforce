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
  onProviderChange,
}: {
  agentId: string;
  model: string;
  savedProviders?: Record<string, Record<string, unknown>>;
  onModelChange: (model: string) => void;
  onProviderChange: (provider: string, patch: { apiKey?: string; apiBase?: string }) => void;
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

  // Custom provider: OpenAI-compatible base URL (snake/camel tolerant)
  const savedBase = selectedProvider && savedProviders?.[selectedProvider]
    ? ((savedProviders[selectedProvider].apiBase ?? savedProviders[selectedProvider].api_base ?? "") as string)
    : "";
  const [apiBase, setApiBase] = useState(savedBase);

  const prevSavedBaseRef = useRef(savedBase);
  useEffect(() => {
    if (savedBase !== prevSavedBaseRef.current) {
      prevSavedBaseRef.current = savedBase;
      setApiBase(savedBase);
    }
  }, [savedBase]);

  const [models, setModels] = useState<FetchedModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelError, setModelError] = useState("");
  const [modelSearch, setModelSearch] = useState("");
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // OAuth state
  const [oauthAuthorized, setOauthAuthorized] = useState<boolean | null>(null);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthPending, setOauthPending] = useState(false); // waiting for user to finish in browser
  const [oauthError, setOauthError] = useState("");
  const [oauthAccountId, setOauthAccountId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const providerDef = PROVIDER_DEFS.find((p) => p.field === selectedProvider);
  // Non-OAuth providers need API keys
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

  // Stop polling when component unmounts or provider changes
  useEffect(() => {
    return () => {
      if (pollRef.current !== null) clearInterval(pollRef.current);
    };
  }, []);

  // Check OAuth status when an OAuth provider is selected
  useEffect(() => {
    if (!providerDef?.oauth) {
      setOauthAuthorized(null);
      setOauthError("");
      setOauthAccountId(null);
      setOauthPending(false);
      if (pollRef.current !== null) { clearInterval(pollRef.current); pollRef.current = null; }
      return;
    }
    setOauthAuthorized(null);
    setOauthError("");
    setOauthAccountId(null);
    setOauthPending(false);
    if (pollRef.current !== null) { clearInterval(pollRef.current); pollRef.current = null; }
    api.providers.oauthStatus(selectedProvider, agentId)
      .then((r) => {
        setOauthAuthorized(r.authorized);
        setOauthAccountId(r.account_id ?? null);
      })
      .catch(() => setOauthAuthorized(false));
  }, [selectedProvider, providerDef?.oauth]);

  function startPolling(provider: string) {
    if (pollRef.current !== null) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await api.providers.oauthStatus(provider, agentId);
        if (r.authorized) {
          setOauthAuthorized(true);
          setOauthAccountId(r.account_id ?? null);
          setOauthPending(false);
          if (pollRef.current !== null) { clearInterval(pollRef.current); pollRef.current = null; }
        }
      } catch { /* ignore poll errors */ }
    }, 2000);
  }

  function cancelPolling() {
    if (pollRef.current !== null) { clearInterval(pollRef.current); pollRef.current = null; }
    setOauthPending(false);
  }

  // Load model list once OAuth provider is authorized; auto-select first model if none chosen
  useEffect(() => {
    if (!providerDef?.oauth || !oauthAuthorized) return;
    setLoadingModels(true);
    setModelError("");
    api.providers.listModels(selectedProvider, "", "")
      .then((r) => {
        setModels(r.models);
        // Auto-select the first model when no model is set for this provider yet
        const currentProviderPrefix = `${selectedProvider}/`;
        const hasModel = model && model.startsWith(currentProviderPrefix);
        if (!hasModel && r.models.length > 0) {
          onModelChange(`${selectedProvider}/${r.models[0].id}`);
        }
      })
      .catch(() => {})
      .finally(() => setLoadingModels(false));
  }, [selectedProvider, oauthAuthorized, providerDef?.oauth]);

  // Auto-fetch models when provider changes (static/API-key providers only)
  useEffect(() => {
    if (!selectedProvider) { setModels([]); return; }
    if (providerDef?.oauth) return; // handled by the OAuth effect above
    const isStatic = ["bedrock", "azure"].includes(selectedProvider);
    const hasSavedKey = !!(savedKey && savedKey.length > 0);
    const isCustom = selectedProvider === "custom";
    const hasSavedBase = !!(savedBase && savedBase.length > 0);
    // Custom needs a base URL; API key is optional (self-hosted endpoints).
    const canAutoFetch = isStatic || (isCustom ? hasSavedBase : hasSavedKey);
    if (canAutoFetch) {
      setLoadingModels(true);
      setModelError("");
      // For saved (redacted) keys/bases, pass agentId so backend uses stored values
      const keyToSend = savedKey.startsWith("***") ? "" : savedKey;
      const baseToSend = savedBase.startsWith("***") ? "" : savedBase;
      api.providers.listModels(
        selectedProvider,
        keyToSend,
        keyToSend && (!isCustom || baseToSend) ? undefined : agentId,
        isCustom ? baseToSend : undefined,
      )
        .then((r) => setModels(r.models))
        .catch(() => {})
        .finally(() => setLoadingModels(false));
    }
  }, [selectedProvider, agentId, savedKey, savedBase, providerDef?.oauth]);

  async function handleOAuthAuthorize() {
    setOauthLoading(true);
    setOauthError("");
    cancelPolling();
    try {
      const r = await api.providers.oauthAuthorize(selectedProvider, agentId);
      window.open(r.auth_url, "_blank", "noopener,noreferrer");
      setOauthPending(true);
      startPolling(selectedProvider);
    } catch (err) {
      setOauthError((err instanceof Error ? err.message : String(err)).replace(/^API \d+: /, ""));
    } finally {
      setOauthLoading(false);
    }
  }

  function doFetch() {
    if (!selectedProvider) return;
    const isCustom = selectedProvider === "custom";
    const hasExplicitKey = apiKey.length > 0 && !apiKey.startsWith("***");
    const hasExplicitBase = apiBase.length > 0 && !apiBase.startsWith("***");
    // Custom requires a base URL; other providers require a key.
    if (isCustom) {
      if (!hasExplicitBase && !savedBase) return;
    } else if (!hasExplicitKey && !savedKey) {
      return;
    }
    setLoadingModels(true);
    setModelError("");
    setModels([]);
    api.providers.listModels(
      selectedProvider,
      hasExplicitKey ? apiKey : "",
      agentId,
      isCustom ? (hasExplicitBase ? apiBase : "") : undefined,
    )
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
    const savedBaseForField = field && savedProviders?.[field]
      ? ((savedProviders[field].apiBase ?? savedProviders[field].api_base ?? "") as string)
      : "";
    setApiBase(typeof savedBaseForField === "string" && !savedBaseForField.startsWith("***") ? savedBaseForField : "");
    setModels([]);
    setModelError("");
    setModelSearch("");
  }

  function handleModelSelect(modelId: string) {
    const fullModel = `${selectedProvider}/${modelId}`;
    // Persist API key / base URL into agent.providers so they're included in "Save Changes"
    if (needsKey) {
      const patch: { apiKey?: string; apiBase?: string } = {};
      if (apiKey && !apiKey.startsWith("***")) patch.apiKey = apiKey;
      if (selectedProvider === "custom" && apiBase && !apiBase.startsWith("***")) patch.apiBase = apiBase;
      if (Object.keys(patch).length > 0) onProviderChange(selectedProvider, patch);
    }
    // OAuth providers: no key to propagate — credentials live in the OS credential store
    onModelChange(fullModel);
    setModelDropdownOpen(false);
    setModelSearch("");
  }

  const currentModelDisplay = model
    ? model.includes("/") ? model.substring(model.indexOf("/") + 1) : model
    : "";

  const hasUsableKey = apiKey.length > 0 || !!(savedKey && savedKey.length > 0);
  const hasUsableBase = apiBase.length > 0 || !!(savedBase && savedBase.length > 0);
  // Custom only needs a base URL to fetch models; API key is optional.
  const canFetchModels = selectedProvider === "custom" ? hasUsableBase : hasUsableKey;

  const filteredModels = modelSearch
    ? models.filter((m) =>
      m.id.toLowerCase().includes(modelSearch.toLowerCase()) ||
      m.name.toLowerCase().includes(modelSearch.toLowerCase())
    )
    : models;

  return (
    <div className="space-y-2.5">
      {/* Row 1: Provider + API Key / OAuth */}
      <div className="flex gap-4 flex-wrap items-end">
        <div className={(needsKey || providerDef?.oauth) ? "min-w-[140px]" : "flex-1 min-w-[160px]"}>
          <label className={css.label}>Provider</label>
          <select
            className={`${css.input} w-full`}
            value={selectedProvider}
            onChange={(e) => handleProviderChange(e.target.value)}
          >
            <option value="">Select a provider…</option>
            <optgroup label="── Subscription (no API key)">
              {PROVIDER_DEFS.filter((p) => p.oauth).map((p) => (
                <option key={p.field} value={p.field}>{p.label}</option>
              ))}
            </optgroup>
            <optgroup label="── API Key">
              {PROVIDER_DEFS.filter((p) => !p.oauth).map((p) => (
                <option key={p.field} value={p.field}>{p.label}</option>
              ))}
            </optgroup>
          </select>
        </div>

        {/* OAuth authorization UI */}
        {selectedProvider && providerDef?.oauth && (
          <div className="flex-1 min-w-[200px]">
            <label className={css.label}>Authorization</label>
            {oauthAuthorized === null && !oauthPending && (
              <p className="text-xs text-claude-text-muted">Checking status…</p>
            )}
            {oauthAuthorized === true && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block shrink-0" />
                  Connected{oauthAccountId ? ` · ${oauthAccountId.slice(0, 8)}…` : ""}
                </span>
                <button
                  type="button"
                  onClick={handleOAuthAuthorize}
                  disabled={oauthLoading}
                  className={`${css.btn} text-xs text-claude-text-muted ring-1 ring-claude-border hover:bg-claude-surface disabled:opacity-40`}
                >
                  Re-authorize
                </button>
              </div>
            )}
            {oauthPending && (
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <svg className="h-3.5 w-3.5 animate-spin text-claude-accent shrink-0" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span className="text-xs text-claude-text-secondary">Waiting for authorization…</span>
                  <button
                    type="button"
                    onClick={cancelPolling}
                    className="text-[11px] text-claude-text-muted hover:text-red-500 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
                <p className="text-[10px] text-claude-text-muted">Complete sign-in in the browser tab that just opened.</p>
              </div>
            )}
            {oauthAuthorized === false && !oauthPending && (
              <div className="flex flex-col gap-1.5">
                <button
                  type="button"
                  onClick={handleOAuthAuthorize}
                  disabled={oauthLoading}
                  className={`${css.btn} text-claude-accent ring-1 ring-claude-accent/30 hover:bg-claude-accent/5 disabled:opacity-40 disabled:cursor-not-allowed`}
                >
                  {oauthLoading ? "Opening browser…" : `Connect ${providerDef.label}`}
                </button>
                {oauthError && <p className="text-xs text-red-500">{oauthError}</p>}
                <p className="text-[10px] text-claude-text-muted">Opens a new tab to authorize</p>
              </div>
            )}
          </div>
        )}

        {/* API key input for non-OAuth providers */}
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

      {/* Base URL input — only for the Custom (OpenAI-compatible) provider */}
      {selectedProvider === "custom" && (
        <div>
          <label className={css.label}>Base URL</label>
          <input
            className={`${css.input} w-full`}
            type="text"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") doFetch(); }}
            placeholder="https://api.example.com/v1"
          />
          <p className="mt-1 text-[10px] text-claude-text-muted">
            Must be an OpenAI API compatible endpoint (e.g. vLLM, LM Studio, a private gateway).
          </p>
        </div>
      )}

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
                    ? (needsKey
                        ? (selectedProvider === "custom"
                            ? (hasUsableBase ? "Click Fetch models to load" : "Enter base URL and fetch models")
                            : (savedKey ? "Click Fetch models to load" : "Enter API key and fetch models"))
                        : providerDef?.oauth
                          ? (oauthAuthorized ? "Select a model…" : "Connect first to browse models")
                          : "Select a provider first")
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
              disabled={!canFetchModels || loadingModels}
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
                const manual = prompt("Enter model ID (e.g. claude-sonnet-4-20250514):", currentModelDisplay);
                if (manual !== null && manual.trim()) {
                  const fullModel = selectedProvider ? `${selectedProvider}/${manual.trim()}` : manual.trim();
                  if (needsKey) {
                    const patch: { apiKey?: string; apiBase?: string } = {};
                    if (apiKey && !apiKey.startsWith("***")) patch.apiKey = apiKey;
                    if (selectedProvider === "custom" && apiBase && !apiBase.startsWith("***")) patch.apiBase = apiBase;
                    if (Object.keys(patch).length > 0) onProviderChange(selectedProvider, patch);
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
