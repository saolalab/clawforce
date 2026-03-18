import { useState } from "react";
import { Link } from "react-router-dom";
import { CHANNEL_DEFS, css } from "../constants";
import { Toggle } from "../ui/Section";
import type { Agent, FieldDef } from "../types";

const SECRET_FIELD_NAMES = new Set([
  "token", "bot_token", "app_token", "app_password",
  "app_secret", "client_secret", "claw_token",
  "imap_password", "smtp_password", "secret",
]);

function isSecretField(f: FieldDef): boolean {
  return f.type === "password" && SECRET_FIELD_NAMES.has(f.name);
}

function LinkWhatsAppInstruction() {
  return (
    <div className="rounded-lg border border-claude-border bg-claude-surface/50 px-3 py-2.5 text-sm">
      <p className="font-medium text-claude-text-primary mb-1">Link your WhatsApp account</p>
      <p className="text-claude-text-muted mb-2">
        Open the terminal in the <strong>Workspace</strong> tab and run:
      </p>
      <code className="block rounded bg-claude-input px-2 py-1.5 font-mono text-xs text-claude-text-secondary">
        clawbot-whatsapp-bridge
      </code>
      <p className="text-claude-text-muted mt-2 text-xs">
        Scan the QR code with WhatsApp (Linked Devices). The session is saved automatically. The bridge will reconnect on next start.
      </p>
    </div>
  );
}

function LinkZaloInstruction() {
  return (
    <div className="rounded-lg border border-claude-border bg-claude-surface/50 px-3 py-2.5 text-sm">
      <p className="font-medium text-claude-text-primary mb-1">Link your Zalo account</p>
      <p className="text-claude-text-muted mb-2">
        Open the terminal in the <strong>Workspace</strong> tab and run:
      </p>
      <code className="block rounded bg-claude-input px-2 py-1.5 font-mono text-xs text-claude-text-secondary">
        clawbot-zalo-personal-bridge
      </code>
      <p className="text-claude-text-muted mt-2 text-xs">
        Scan the QR code with Zalo. The session is saved automatically.
      </p>
    </div>
  );
}

export function ChannelsTab({
  agent,
  updateChannel,
}: {
  agent: Agent;
  updateChannel: (ch: string, patch: Record<string, unknown>) => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const whatsappBridgeInstalled = !!(agent.tools?.software?.["whatsapp-bridge"]);
  const zaloBridgeInstalled = !!(agent.tools?.software?.["zalo-personal-bridge"]);

  // Token/secret fields live in agent.channels; typing updates agent so the main Save persists them.
  function getTokenValue(chKey: string, fieldName: string): string {
    const ch = (agent.channels[chKey] || {}) as Record<string, unknown>;
    const v = ch[fieldName];
    return typeof v === "string" ? v : "";
  }

  return (
    <div className="space-y-2">
      {CHANNEL_DEFS.map((ch) => {
        const data = (agent.channels[ch.key] || {}) as Record<string, unknown>;
        const isEnabled = !!data.enabled;
        const isOpen = expanded === ch.key;
        const isZalo = ch.key === "zalouser";
        const isWhatsApp = ch.key === "whatsapp";
        const bridgeUnavailable = (isZalo && !zaloBridgeInstalled) || (isWhatsApp && !whatsappBridgeInstalled);

        return (
          <div key={ch.key} className={css.card}>
            <button type="button" onClick={() => setExpanded(isOpen ? null : ch.key)} className="flex w-full items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="flex items-center justify-center w-5 h-5 shrink-0">{ch.icon}</span>
                <span className="text-sm font-medium text-claude-text-primary">{ch.label}</span>
                {isEnabled && (
                  <span className="rounded-full bg-green-50 px-1.5 py-px text-[10px] font-medium text-green-700 ring-1 ring-green-200">Active</span>
                )}
              </div>
              <svg
                className={`h-4 w-4 text-claude-text-muted transition-transform ${isOpen ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {isOpen && (
              <div className="mt-3 space-y-2.5 border-t border-claude-border pt-3">
                {isZalo && !zaloBridgeInstalled && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
                    <p className="font-medium">Zalo Personal Bridge is not available</p>
                    <p className="mt-1 text-amber-700">
                      Install it from{" "}
                      <Link to="/marketplace#software" className="text-claude-accent hover:underline font-medium">
                        Marketplace → Software catalog
                      </Link>
                      , then ensure the bridge is running with your agent.
                    </p>
                  </div>
                )}
                {isWhatsApp && !whatsappBridgeInstalled && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-800">
                    <p className="font-medium">WhatsApp Bridge is not available</p>
                    <p className="mt-1 text-amber-700">
                      Install it from{" "}
                      <Link to="/marketplace#software" className="text-claude-accent hover:underline font-medium">
                        Marketplace → Software catalog
                      </Link>
                      , then ensure the bridge is running with your agent.
                    </p>
                  </div>
                )}
                {ch.fields.map((f) => {
                  // Zalo/WhatsApp: disable toggle when bridge not available
                  if ((isZalo || isWhatsApp) && f.type === "toggle" && bridgeUnavailable) {
                    return (
                      <div key={f.name} className="flex items-center gap-2.5 opacity-60">
                        <div className={`${css.toggle} bg-claude-border-strong cursor-not-allowed`}>
                          <span className="pointer-events-none block h-4 w-4 rounded-full bg-white shadow-sm translate-x-0" />
                        </div>
                        <span className="text-sm text-claude-text-muted">{f.label}</span>
                        <span className="text-xs text-claude-text-muted">(install bridge first)</span>
                      </div>
                    );
                  }

                  // Token/secret fields — managed via secrets endpoint
                  if (isSecretField(f)) {
                    return (
                      <div key={f.name}>
                        <label className={css.label}>{f.label}</label>
                        <input
                          className={css.input}
                          type="password"
                          value={getTokenValue(ch.key, f.name)}
                          onChange={(e) => updateChannel(ch.key, { [f.name]: e.target.value })}
                          placeholder={f.placeholder}
                          autoComplete="new-password"
                          disabled={bridgeUnavailable}
                        />
                      </div>
                    );
                  }

                  const value = data[f.name];

                  if (f.type === "toggle") {
                    return (
                      <Toggle
                        key={f.name}
                        checked={!!value}
                        onChange={(v) => updateChannel(ch.key, { [f.name]: v })}
                        label={f.label}
                      />
                    );
                  }

                  if (f.type === "tags") {
                    const display = Array.isArray(value) ? (value as string[]).join(", ") : ((value as string) || "");
                    return (
                      <div key={f.name}>
                        <label className={css.label}>{f.label}</label>
                        <input
                          className={css.input}
                          value={display}
                          onChange={(e) => updateChannel(ch.key, { [f.name]: e.target.value })}
                          placeholder={f.placeholder}
                          disabled={bridgeUnavailable}
                        />
                        <span className="text-[10px] text-claude-text-muted mt-0.5 block">Comma-separated values</span>
                      </div>
                    );
                  }

                  return (
                    <div key={f.name}>
                      <label className={css.label}>{f.label}</label>
                      <input
                        className={css.input}
                        type={f.type}
                        value={(value as string | number) ?? ""}
                        onChange={(e) => {
                          const v = f.type === "number" ? parseInt(e.target.value) || 0 : e.target.value;
                          updateChannel(ch.key, { [f.name]: v });
                        }}
                        placeholder={f.placeholder}
                        disabled={bridgeUnavailable}
                      />
                    </div>
                  );
                })}
                {isZalo && zaloBridgeInstalled && (
                  <div className="pt-2">
                    <LinkZaloInstruction />
                  </div>
                )}
                {isWhatsApp && whatsappBridgeInstalled && (
                  <div className="pt-2">
                    <LinkWhatsAppInstruction />
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
