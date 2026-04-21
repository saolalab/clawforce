import { useState } from "react";
import { api } from "../lib/api";
import { CHANNEL_DEFS, css } from "./agent-detail/constants";
import { ChannelsTab } from "./agent-detail/settings/ChannelsTab";
import { ModelProviderSection } from "./agent-detail/settings/ModelProviderSection";
import type { Agent } from "./agent-detail/types";
import Modal from "./Modal";

const CHANNEL_SECRET_KEYS = new Set(
  CHANNEL_DEFS.flatMap((ch) => ch.fields.filter((f) => f.type === "password").map((f) => f.name))
);

const PROVIDER_SECRET_KEYS = new Set(["apiKey", "api_key"]);

function channelsPayloadForUpdate(channels: Record<string, Record<string, unknown>>): Record<string, Record<string, unknown>> {
  const out: Record<string, Record<string, unknown>> = {};
  for (const [chKey, chData] of Object.entries(channels)) {
    if (!chData || typeof chData !== "object") {
      out[chKey] = chData as Record<string, unknown>;
      continue;
    }
    const filtered: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(chData)) {
      if (CHANNEL_SECRET_KEYS.has(k) && typeof v === "string" && v.startsWith("***")) continue;
      filtered[k] = v;
    }
    out[chKey] = filtered;
  }
  return out;
}

function providersPayloadForUpdate(providers: Record<string, Record<string, unknown>> | undefined): Record<string, Record<string, unknown>> | undefined {
  if (!providers || typeof providers !== "object") return undefined;
  const out: Record<string, Record<string, unknown>> = {};
  for (const [pKey, pData] of Object.entries(providers)) {
    if (!pData || typeof pData !== "object") continue;
    const filtered: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(pData)) {
      if (PROVIDER_SECRET_KEYS.has(k) && typeof v === "string" && v.startsWith("***")) continue;
      filtered[k] = v;
    }
    if (Object.keys(filtered).length > 0) out[pKey] = filtered;
  }
  return Object.keys(out).length ? out : undefined;
}

function hasChannelEnabled(channels: Record<string, Record<string, unknown>>): boolean {
  for (const chData of Object.values(channels)) {
    if (chData && typeof chData === "object" && chData.enabled) return true;
  }
  return false;
}

export function OnboardingWizardModal({
  agent,
  onClose,
  onComplete,
}: {
  agent: Agent;
  onClose: () => void;
  onComplete: () => void;
}) {
  const modelAlreadyConfigured = !!(agent.model && agent.model.trim());
  const [step, setStep] = useState<1 | 2>(modelAlreadyConfigured ? 2 : 1);
  const [wizardAgent, setWizardAgent] = useState<Agent>(() => ({ ...agent }));
  const [saving, setSaving] = useState(false);

  const modelConfigured = !!(wizardAgent.model && wizardAgent.model.trim());
  const channelConfigured = hasChannelEnabled(wizardAgent.channels || {});
  const canComplete = modelConfigured || channelConfigured;

  function update(patch: Partial<Agent>) {
    setWizardAgent((a) => ({ ...a, ...patch }));
  }

  function updateChannel(ch: string, patch: Record<string, unknown>) {
    setWizardAgent((a) => ({
      ...a,
      channels: { ...a.channels, [ch]: { ...(a.channels[ch] || {}), ...patch } },
    }));
  }

  async function handleSkip() {
    if (!agent.id) return;
    setSaving(true);
    try {
      await api.agents.update(agent.id, { onboarding_completed: true });
      onComplete();
      onClose();
    } catch (err) {
      alert(`Failed to save: ${err instanceof Error ? err.message : err}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleComplete() {
    if (!agent.id || !canComplete) return;
    setSaving(true);
    try {
      const channels = structuredClone(wizardAgent.channels || {});
      for (const chDef of CHANNEL_DEFS) {
        const chData = channels[chDef.key];
        if (!chData) continue;
        for (const field of chDef.fields) {
          if (field.type === "tags" && typeof chData[field.name] === "string") {
            chData[field.name] = (chData[field.name] as string)
              .split(",")
              .map((s: string) => s.trim())
              .filter(Boolean);
          }
        }
      }
      const channelsToSend = channelsPayloadForUpdate(channels);
      const providersToSend = providersPayloadForUpdate(wizardAgent.providers as Record<string, Record<string, unknown>> | undefined);

      const payload: Record<string, unknown> = {
        onboarding_completed: true,
        model: wizardAgent.model,
        channels: channelsToSend,
      };
      if (providersToSend) payload.providers = providersToSend;

      await api.agents.update(agent.id, payload);
      onComplete();
      onClose();
    } catch (err) {
      alert(`Failed to save: ${err instanceof Error ? err.message : err}`);
    } finally {
      setSaving(false);
    }
  }

  const steps = [
    { num: 1, label: "Model Provider" },
    { num: 2, label: "Channels" },
  ];

  return (
    <Modal
      open
      onClose={onClose}
      title="Agent Setup"
      size="xl"
      footer={
        <div className="flex w-full items-center justify-between">
          <div className="flex gap-2">
            {step === 2 && (
              <button
                type="button"
                onClick={() => setStep(1)}
                className={`${css.btn} text-claude-text-muted hover:text-claude-text-secondary`}
              >
                Back
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSkip}
              disabled={saving}
              className={`${css.btn} text-claude-text-muted hover:text-claude-text-secondary disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              Skip
            </button>
            {step === 1 ? (
              <button
                type="button"
                onClick={() => setStep(2)}
                className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover`}
              >
                Next
              </button>
            ) : (
              <button
                type="button"
                onClick={handleComplete}
                disabled={!canComplete || saving}
                className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {saving ? (
                  <span className="flex items-center gap-2">
                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Saving…
                  </span>
                ) : (
                  "Complete Setup"
                )}
              </button>
            )}
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        <div className="flex gap-4 border-b border-claude-border pb-3">
          {steps.map((s) => (
            <button
              key={s.num}
              type="button"
              onClick={() => setStep(s.num as 1 | 2)}
              className={`flex items-center gap-2 text-sm font-medium transition-colors ${
                step === s.num
                  ? "text-claude-accent"
                  : "text-claude-text-muted hover:text-claude-text-secondary"
              }`}
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs ${
                  step === s.num
                    ? "bg-claude-accent/10 text-claude-accent"
                    : "bg-claude-surface text-claude-text-muted"
                }`}
              >
                {s.num}
              </span>
              {s.label}
            </button>
          ))}
        </div>

        {step === 1 && (
          <div className="min-h-[360px]">
            <h3 className="text-sm font-medium text-claude-text-primary mb-3">Configure your LLM provider and model</h3>
            <ModelProviderSection
              agentId={agent.id}
              model={wizardAgent.model}
              savedProviders={wizardAgent.providers as Record<string, Record<string, unknown>> | undefined}
              onModelChange={(v) => update({ model: v })}
              onProviderChange={(provider, patch) => {
                update({
                  providers: {
                    ...wizardAgent.providers,
                    [provider]: { ...(wizardAgent.providers?.[provider] || {}), ...patch },
                  },
                });
              }}
            />
          </div>
        )}

        {step === 2 && (
          <div>
            <h3 className="text-sm font-medium text-claude-text-primary mb-3">Configure at least one channel to receive tasks</h3>
            <ChannelsTab agent={wizardAgent} updateChannel={updateChannel} />
          </div>
        )}

        {!canComplete && step === 2 && (
          <p className="text-xs text-claude-text-muted">
            Configure a model (Step 1) or enable at least one channel to complete setup.
          </p>
        )}
      </div>
    </Modal>
  );
}
