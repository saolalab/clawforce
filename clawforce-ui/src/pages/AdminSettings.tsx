import { useState, useEffect, useCallback } from "react";
import {
  api,
  type RuntimeInfo,
} from "../lib/api";
import { Card, PageHeader, PageContainer, Button, Input } from "../components/ui";

type TabType = "general" | "password";

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
      />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function RuntimeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
    </svg>
  );
}


const selectCls =
  "w-full rounded-lg border border-claude-border bg-claude-bg px-3 py-2 text-sm text-claude-text-primary focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20fill%3D%22%239B958F%22%20viewBox%3D%220%200%2016%2016%22%3E%3Cpath%20d%3D%22M4.646%206.646a.5.5%200%2001.708%200L8%209.293l2.646-2.647a.5.5%200%2001.708.708l-3%203a.5.5%200%2001-.708%200l-3-3a.5.5%200%20010-.708z%22%2F%3E%3C%2Fsvg%3E')] bg-[length:16px] bg-[right_8px_center] bg-no-repeat pr-8";

function SectionHeader({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="flex items-start gap-3 mb-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-claude-surface">
        {icon}
      </div>
      <div className="min-w-0">
        <h2 className="text-sm font-semibold text-claude-text-primary">{title}</h2>
        <p className="mt-0.5 text-xs text-claude-text-muted leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
      <svg className="h-4 w-4 shrink-0 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      <p className="text-xs text-red-700">{message}</p>
    </div>
  );
}

function LockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm6-10V7a3 3 0 00-3-3H9a3 3 0 00-3 3v2h12z" />
    </svg>
  );
}

function InfoIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function SuccessBanner({ message }: { message: string }) {
  return (
    <div className="mb-4 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3 py-2">
      <svg className="h-4 w-4 shrink-0 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p className="text-xs text-green-700">{message}</p>
    </div>
  );
}

export default function AdminSettings() {
  const [activeTab, setActiveTab] = useState<TabType>("general");
  const [runtimeInfo, setRuntimeInfo] = useState<RuntimeInfo | null>(null);
  const [runtimeError, setRuntimeError] = useState("");
  const [runtimeSwitching, setRuntimeSwitching] = useState(false);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [passwordChanging, setPasswordChanging] = useState(false);

  const fetchRuntimeInfo = useCallback(async () => {
    try {
      setRuntimeError("");
      const info = await api.runtime.info();
      setRuntimeInfo(info);
    } catch (e) {
      setRuntimeError(e instanceof Error ? e.message : "Failed to load runtime info");
    }
  }, []);


  useEffect(() => {
    fetchRuntimeInfo();
  }, [fetchRuntimeInfo]);

  async function handleRuntimeBackendChange(kind: string) {
    if (!runtimeInfo || kind === runtimeInfo.runtime_type) return;
    setRuntimeSwitching(true);
    setRuntimeError("");
    try {
      await api.runtime.setBackend(kind);
      await fetchRuntimeInfo();
    } catch (e) {
      setRuntimeError(e instanceof Error ? e.message : "Failed to switch backend");
    } finally {
      setRuntimeSwitching(false);
    }
  }

  async function handlePasswordChange() {
    setPasswordError("");
    setPasswordSuccess("");

    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError("All fields are required");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match");
      return;
    }

    if (newPassword.length < 6) {
      setPasswordError("New password must be at least 6 characters");
      return;
    }

    setPasswordChanging(true);
    try {
      await api.auth.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordSuccess("Password changed successfully");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setPasswordSuccess(""), 5000);
    } catch (e) {
      setPasswordError(e instanceof Error ? e.message : "Failed to change password");
    } finally {
      setPasswordChanging(false);
    }
  }


  return (
    <PageContainer>
      <PageHeader
        title="Settings"
        icon={<SettingsIcon className="h-5 w-5" />}
        description="Global configuration for the admin platform."
      />

      {/* ── Tab Navigation ────────────────────────────────────── */}
      <div className="mb-6 border-b border-claude-border">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab("general")}
            className={`py-3 px-1 font-medium text-sm border-b-2 transition-colors ${
              activeTab === "general"
                ? "border-claude-accent text-claude-accent"
                : "border-transparent text-claude-text-muted hover:text-claude-text-primary"
            }`}
          >
            General
          </button>
          <button
            onClick={() => setActiveTab("password")}
            className={`py-3 px-1 font-medium text-sm border-b-2 transition-colors ${
              activeTab === "password"
                ? "border-claude-accent text-claude-accent"
                : "border-transparent text-claude-text-muted hover:text-claude-text-primary"
            }`}
          >
            Password
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {/* ── General Tab ──────────────────────────────────────── */}
        {activeTab === "general" && (
          <>
            {runtimeInfo && (
              <Card>
                <SectionHeader
                  icon={<InfoIcon className="h-4 w-4 text-claude-text-muted" />}
                  title="Setup info"
                  description="System configuration and storage details"
                />

                {runtimeInfo.data_root && (
                  <div className="max-w-sm">
                    <label className="mb-1 block text-xs font-medium text-claude-text-muted">Root storage path</label>
                    <div className="flex items-center gap-2 rounded-lg bg-claude-surface px-3 py-2">
                      <svg className="h-3.5 w-3.5 shrink-0 text-claude-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                      </svg>
                      <span className="text-xs text-claude-text-primary font-mono break-all">{runtimeInfo.data_root}</span>
                    </div>
                  </div>
                )}
              </Card>
            )}

            <Card>
              <SectionHeader
                icon={<RuntimeIcon className="h-4 w-4 text-claude-text-muted" />}
                title="Agent runtime backend"
                description="Controls how agents are executed. All agents share this backend. Stop all running agents before switching."
              />

              {runtimeError && <ErrorBanner message={runtimeError} />}

              {runtimeInfo ? (
                <div className="space-y-3">
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-claude-text-muted">Backend</label>
                    <div className="max-w-sm">
                      <select
                        value={runtimeInfo.runtime_type}
                        onChange={(e) => handleRuntimeBackendChange(e.target.value)}
                        disabled={runtimeSwitching}
                        className={selectCls + (runtimeSwitching ? " opacity-50 cursor-wait" : "")}
                      >
                        {runtimeInfo.available_backends.map((b) => (
                          <option key={b.value} value={b.value}>{b.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {runtimeInfo.running_count > 0 && (
                    <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
                      <svg className="h-4 w-4 shrink-0 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                      </svg>
                      <p className="text-xs text-amber-700">
                        <span className="font-medium">{runtimeInfo.running_count} agent(s) running</span> — stop all before switching backend.
                      </p>
                    </div>
                  )}
                </div>
              ) : !runtimeError ? (
                <div className="flex items-center gap-2 py-2">
                  <svg className="h-4 w-4 animate-spin text-claude-text-muted" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <p className="text-xs text-claude-text-muted">Loading runtime info…</p>
                </div>
              ) : null}
            </Card>
          </>
        )}

        {/* ── Password Tab ──────────────────────────────────────── */}
        {activeTab === "password" && (
          <Card>
            <SectionHeader
              icon={<LockIcon className="h-4 w-4 text-claude-text-muted" />}
              title="Change password"
              description="Update your admin account password."
            />

            {passwordError && <ErrorBanner message={passwordError} />}
            {passwordSuccess && <SuccessBanner message={passwordSuccess} />}

            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-claude-text-muted">Current password</label>
                <Input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  disabled={passwordChanging}
                  className="w-[400px] max-w-full"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-claude-text-muted">New password</label>
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  disabled={passwordChanging}
                  className="w-[400px] max-w-full"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-claude-text-muted">Confirm new password</label>
                <Input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  disabled={passwordChanging}
                  className="w-[400px] max-w-full"
                />
              </div>
              <Button
                onClick={handlePasswordChange}
                disabled={passwordChanging}
              >
                {passwordChanging ? "Changing..." : "Change Password"}
              </Button>
            </div>
          </Card>
        )}
      </div>
    </PageContainer>
  );
}
