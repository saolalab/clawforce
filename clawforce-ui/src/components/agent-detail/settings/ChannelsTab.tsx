import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import QRCode from "qrcode";
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

/** Zalo bridge admin API is on port 3003 (bridge port 3002 + 1). */
const ZALO_ADMIN_URL = "http://localhost:3003";
/** WhatsApp bridge admin API is on port 3002 (bridge port 3001 + 1). */
const WHATSAPP_ADMIN_URL = "http://localhost:3002";

async function checkBridgeAvailable(adminUrl: string): Promise<boolean> {
  try {
    const res = await fetch(`${adminUrl}/admin/qr`);
    return res.ok || res.status === 404;
  } catch {
    return false;
  }
}

async function fetchBridgeQR(adminUrl: string): Promise<{ qr: string; timestamp: number } | null> {
  try {
    const res = await fetch(`${adminUrl}/admin/qr`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.qr ? { qr: data.qr, timestamp: data.timestamp ?? Date.now() } : null;
  } catch {
    return null;
  }
}

async function refreshBridgeQR(adminUrl: string): Promise<boolean> {
  try {
    const res = await fetch(`${adminUrl}/admin/qr/refresh`, { method: "POST" });
    return res.ok;
  } catch {
    return false;
  }
}

function BridgeQRModal({
  title,
  scanHint,
  adminUrl,
  onClose,
}: {
  title: string;
  scanHint: string;
  adminUrl: string;
  onClose: () => void;
}) {
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const data = await fetchBridgeQR(adminUrl);
      if (cancelled) return;
      if (data?.qr) {
        try {
          const url = await QRCode.toDataURL(data.qr, { width: 256, margin: 2 });
          setQrDataUrl(url);
        } catch {
          setError("Failed to render QR code");
        }
      } else {
        setError("No QR code available. The bridge may already be connected.");
      }
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [adminUrl]);

  const handleRefresh = async () => {
    setRefreshing(true);
    const ok = await refreshBridgeQR(adminUrl);
    setRefreshing(false);
    if (ok) {
      const data = await fetchBridgeQR(adminUrl);
      if (data?.qr) {
        const url = await QRCode.toDataURL(data.qr, { width: 256, margin: 2 });
        setQrDataUrl(url);
        setError(null);
      }
    } else {
      setError("Refresh failed. The bridge may already be authenticated.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="rounded-xl border border-claude-border bg-claude-bg p-6 shadow-xl max-w-sm w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-sm font-semibold text-claude-text-primary mb-3">{title}</h3>
        <p className="text-xs text-claude-text-muted mb-4">{scanHint}</p>
        {loading && <p className="text-sm text-claude-text-muted py-8">Loading...</p>}
        {error && !loading && <p className="text-sm text-amber-600 py-4">{error}</p>}
        {qrDataUrl && (
          <div className="flex flex-col items-center gap-4">
            <img src={qrDataUrl} alt="QR Code" className="rounded-lg border border-claude-border" />
            <button
              type="button"
              onClick={handleRefresh}
              disabled={refreshing}
              className="rounded-lg px-3 py-1.5 text-sm font-medium bg-claude-accent text-white hover:opacity-90 disabled:opacity-50"
            >
              {refreshing ? "Refreshing..." : "Refresh QR Code"}
            </button>
          </div>
        )}
        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-lg border border-claude-border px-3 py-1.5 text-sm text-claude-text-secondary hover:bg-claude-surface"
        >
          Close
        </button>
      </div>
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
  const [zaloAvailable, setZaloAvailable] = useState<boolean | null>(null);
  const [whatsappAvailable, setWhatsAppAvailable] = useState<boolean | null>(null);
  const [zaloQRModal, setZaloQRModal] = useState(false);
  const [whatsappQRModal, setWhatsAppQRModal] = useState(false);

  useEffect(() => {
    if (expanded !== "zalouser") return;
    let cancelled = false;
    checkBridgeAvailable(ZALO_ADMIN_URL).then((ok) => {
      if (!cancelled) setZaloAvailable(ok);
    });
    return () => { cancelled = true; };
  }, [expanded]);

  useEffect(() => {
    if (expanded !== "whatsapp") return;
    let cancelled = false;
    checkBridgeAvailable(WHATSAPP_ADMIN_URL).then((ok) => {
      if (!cancelled) setWhatsAppAvailable(ok);
    });
    return () => { cancelled = true; };
  }, [expanded]);

  // Token/secret fields live in agent.channels; typing updates agent so the main Save persists them.
  function getTokenValue(chKey: string, fieldName: string): string {
    const ch = (agent.channels[chKey] || {}) as Record<string, unknown>;
    const v = ch[fieldName];
    return typeof v === "string" ? v : "";
  }

  return (
    <div className="space-y-2">
      {zaloQRModal && (
        <BridgeQRModal
          title="Zalo QR Code"
          scanHint="Scan with Zalo app to link your account"
          adminUrl={ZALO_ADMIN_URL}
          onClose={() => setZaloQRModal(false)}
        />
      )}
      {whatsappQRModal && (
        <BridgeQRModal
          title="WhatsApp QR Code"
          scanHint="Scan with WhatsApp (Linked Devices) to link your account"
          adminUrl={WHATSAPP_ADMIN_URL}
          onClose={() => setWhatsAppQRModal(false)}
        />
      )}
      {CHANNEL_DEFS.map((ch) => {
        const data = (agent.channels[ch.key] || {}) as Record<string, unknown>;
        const isEnabled = !!data.enabled;
        const isOpen = expanded === ch.key;
        const isZalo = ch.key === "zalouser";
        const isWhatsApp = ch.key === "whatsapp";
        const zaloEndpointAvailable = isZalo ? zaloAvailable === true : true;
        const whatsappEndpointAvailable = isWhatsApp ? whatsappAvailable === true : true;
        const bridgeUnavailable = (isZalo && !zaloEndpointAvailable) || (isWhatsApp && !whatsappEndpointAvailable);

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
                {isZalo && !zaloEndpointAvailable && (
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
                {isWhatsApp && !whatsappEndpointAvailable && (
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
                {isZalo && zaloEndpointAvailable && (
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => setZaloQRModal(true)}
                      className="rounded-lg border border-claude-border px-3 py-1.5 text-sm font-medium text-claude-text-primary hover:bg-claude-surface"
                    >
                      Show QR Code
                    </button>
                  </div>
                )}
                {isWhatsApp && whatsappEndpointAvailable && (
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => setWhatsAppQRModal(true)}
                      className="rounded-lg border border-claude-border px-3 py-1.5 text-sm font-medium text-claude-text-primary hover:bg-claude-surface"
                    >
                      Show QR Code
                    </button>
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
