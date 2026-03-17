import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { ClawIcon } from "../components/ClawIcon";
import { OnboardingWizardModal } from "../components/OnboardingWizardModal";
import { Breadcrumb, PageContainer } from "../components/ui";
import { api } from "../lib/api";
import { css, CHANNEL_DEFS } from "../components/agent-detail/constants";
import { deepMerge, defaultTools, defaultSkills, defaultHeartbeat } from "../components/agent-detail/utils";
import { WorkspaceTab } from "../components/agent-detail/workspace/WorkspaceTab";
import { LogsTab } from "../components/agent-detail/logs/LogsTab";
import { ScheduledJobsTab } from "../components/agent-detail/settings/ScheduledJobsTab";
import { SettingsContent } from "../components/agent-detail/settings/SettingsContent";
import type { Agent, MainTab, ToolsCfg } from "../components/agent-detail/types";

/** Secret field names (from CHANNEL_DEFS password fields). Omit these when value is redacted so backend keeps existing. */
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
      if (CHANNEL_SECRET_KEYS.has(k) && typeof v === "string" && v.startsWith("***")) {
        continue; // omit redacted secrets so backend merge keeps existing values
      }
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

export default function AgentDetail() {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [lastSavedAgent, setLastSavedAgent] = useState<Agent | null>(null);
  const [mainTab, setMainTab] = useState<MainTab>("workspace");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [onboardingDismissed, setOnboardingDismissed] = useState(false);
  const [showOnboardingModal, setShowOnboardingModal] = useState(false);

  const ONBOARDING_DELAY_MS = 2500;

  useEffect(() => {
    setOnboardingDismissed(false);
    setShowOnboardingModal(false);
  }, [agentId]);

  useEffect(() => {
    if (!agent || !agentId || agent.id !== agentId || agent.onboarding_completed !== false || onboardingDismissed) {
      setShowOnboardingModal(false);
      return;
    }
    const timer = setTimeout(() => setShowOnboardingModal(true), ONBOARDING_DELAY_MS);
    return () => clearTimeout(timer);
  }, [agent?.id, agent?.onboarding_completed, agentId, onboardingDismissed]);

  useEffect(() => {
    if (!agentId) return;
    api.agents.get(agentId).then((data) => {
      if (!data.tools) data.tools = defaultTools();
      if (!data.skills) data.skills = defaultSkills();
      if (!data.channels) data.channels = {};
      if (!data.providers) data.providers = {};
      if (!data.heartbeat) data.heartbeat = defaultHeartbeat();
      if (!data.security) data.security = {};
      const a = data as Agent;
      setAgent(a);
      setLastSavedAgent(a);
    });
  }, [agentId, token]);

  // Poll status while provisioning or connecting. Trust API response; no heuristics.
  useEffect(() => {
    if (!agentId || !agent) return;
    if (agent.status !== "provisioning" && agent.status !== "connecting") return;

    const interval = setInterval(() => {
      api.agents.get(agentId)
        .then((data) => {
          if (!data.tools) data.tools = defaultTools();
          if (!data.skills) data.skills = defaultSkills();
          if (!data.channels) data.channels = {};
          if (!data.heartbeat) data.heartbeat = defaultHeartbeat();
          if (!data.security) data.security = {};
          setAgent(data as Agent);
        })
        .catch(() => {});
    }, 500);

    return () => clearInterval(interval);
  }, [agentId, agent?.status, token]);

  // Poll MCP status when agent is running and user is on Settings tab (where it's shown)
  useEffect(() => {
    if (!agentId || !agent || agent.status !== "running" || mainTab !== "settings") return;

    const fetch = () =>
      api.mcp.listServers(agentId)
        .then((data) => {
          setAgent((a) => (a ? { ...a, mcp_status: data.servers } : null));
        })
        .catch(() => { });

    fetch();
    const interval = setInterval(fetch, 10000);
    return () => clearInterval(interval);
  }, [agentId, agent?.status, mainTab, token]);

  // Poll agent when running and software reinstall in progress (to update when it completes)
  useEffect(() => {
    if (!agentId || !agent || agent.status !== "running") return;
    if (!agent.software_installing && !(agent.software_warnings?.length)) return;

    const interval = setInterval(() => {
      api.agents.get(agentId)
        .then((data) => {
          if (!data.tools) data.tools = defaultTools();
          if (!data.skills) data.skills = defaultSkills();
          if (!data.channels) data.channels = {};
          if (!data.providers) data.providers = {};
          if (!data.heartbeat) data.heartbeat = defaultHeartbeat();
          if (!data.security) data.security = {};
          setAgent(data as Agent);
        })
        .catch(() => {});
    }, 5000);

    return () => clearInterval(interval);
  }, [agentId, agent?.status, agent?.software_installing, agent?.software_warnings?.length, token]);

  async function refreshAgent() {
    if (!agentId) return;
    try {
      const data = await api.agents.get(agentId);
      if (!data.tools) data.tools = defaultTools();
      if (!data.skills) data.skills = defaultSkills();
      if (!data.channels) data.channels = {};
      if (!data.providers) data.providers = {};
      if (!data.heartbeat) data.heartbeat = defaultHeartbeat();
      if (!data.security) data.security = {};
      setAgent(data as Agent);
    } catch {
      /* ignore */
    }
  }

  function update(patch: Partial<Agent>) {
    setAgent((a) => (a ? { ...a, ...patch } : null));
    setDirty(true);
  }

  function updateTools(patch: Record<string, unknown>) {
    setAgent((a) => (a ? { ...a, tools: deepMerge(a.tools, patch) } : null));
    setDirty(true);
  }

  function setTools(tools: ToolsCfg) {
    setAgent((a) => (a ? { ...a, tools } : null));
    setDirty(true);
  }

  function updateChannel(ch: string, patch: Record<string, unknown>) {
    setAgent((a) => (a ? { ...a, channels: { ...a.channels, [ch]: { ...(a.channels[ch] || {}), ...patch } } } : null));
    setDirty(true);
  }

  function updateSkills(disabled: string[]) {
    setAgent((a) => (a ? { ...a, skills: { disabled } } : null));
    setDirty(true);
  }

  async function save() {
    if (!agentId || !agent) return;
    setSaving(true);
    try {
      const channels = structuredClone(agent.channels);
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
      const providersToSend = providersPayloadForUpdate(agent.providers as Record<string, Record<string, unknown>> | undefined);

      const payload: Record<string, unknown> = {
        name: agent.name,
        description: agent.description,
        color: agent.color,
        model: agent.model,
        temperature: agent.temperature,
        max_tokens: agent.max_tokens,
        max_tool_iterations: agent.max_tool_iterations,
        memory_window: agent.memory_window,
        fault_tolerance: agent.fault_tolerance,
        enabled: agent.enabled,
        tools: agent.tools,
        skills: agent.skills,
        channels: channelsToSend,
        heartbeat: agent.heartbeat,
        security: agent.security,
      };
      if (providersToSend) payload.providers = providersToSend;

      await api.agents.update(agentId, payload);
      const updated = await api.agents.get(agentId);
      if (!updated.tools) updated.tools = defaultTools();
      if (!updated.skills) updated.skills = defaultSkills();
      if (!updated.channels) updated.channels = {};
      if (!updated.heartbeat) updated.heartbeat = defaultHeartbeat();
      if (!updated.security) updated.security = {};
      const updatedAgent = updated as Agent;
      setAgent(updatedAgent);
      setLastSavedAgent(updatedAgent);
      setDirty(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("API 503")) {
        alert("Cannot save: Agent is offline. Start the agent first, then save.");
      } else {
        alert(`Failed to save settings: ${msg}`);
      }
    } finally {
      setSaving(false);
    }
  }

  async function startAgent() {
    setAgent((a) => (a ? { ...a, status: "provisioning" } : null));
    try {
      await api.agents.start(agentId!);
    } catch (err) {
      setAgent((a) => (a ? { ...a, status: "stopped" } : null));
      alert(`Failed to start agent: ${err instanceof Error ? err.message : err}`);
    }
  }

  async function stopAgent() {
    try {
      await api.agents.stop(agentId!);
      setAgent((a) => (a ? { ...a, status: "stopped" } : null));
    } catch (err) {
      alert(`Failed to stop agent: ${err instanceof Error ? err.message : err}`);
    }
  }

  function onDeleted() {
    navigate("/claws");
  }

  if (!agent) return <div className="p-4 text-sm text-claude-text-muted">Loading…</div>;

  const showOnboarding = showOnboardingModal;

  const mainTabs: { key: MainTab; label: string }[] = [
    { key: "workspace", label: "Workspace" },
    { key: "logs", label: "Logs" },
    { key: "jobs", label: "Schedule" },
    { key: "settings", label: "Settings" },
  ];

  return (
    <PageContainer>
      {showOnboarding && (
        <OnboardingWizardModal
          agent={agent}
          onClose={() => setOnboardingDismissed(true)}
          onComplete={async () => {
            const data = await api.agents.get(agentId!);
            if (!data.tools) data.tools = defaultTools();
            if (!data.skills) data.skills = defaultSkills();
            if (!data.channels) data.channels = {};
            if (!data.providers) data.providers = {};
            if (!data.heartbeat) data.heartbeat = defaultHeartbeat();
            if (!data.security) data.security = {};
            setAgent(data as Agent);
          }}
        />
      )}
      <Breadcrumb items={[
        { label: "Claws", to: "/claws" },
        { label: agent?.name ?? "Agent" },
      ]} />
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClawIcon className="h-5 w-5 shrink-0" color={agent.color || undefined} />
          <h1 className="text-lg font-semibold text-claude-text-primary">{agent.name}</h1>
          <span
            className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium ${agent.status === "running"
                ? "bg-green-50 text-green-700 ring-1 ring-green-200"
                : agent.status === "provisioning" || agent.status === "connecting"
                  ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                  : agent.status === "failed"
                    ? "bg-red-50 text-red-700 ring-1 ring-red-200"
                    : "bg-claude-surface text-claude-text-muted ring-1 ring-claude-border"
              }`}
          >
            {agent.status === "running" && (
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
              </span>
            )}
            {agent.status === "running" && agent.software_installing && (
              <svg className="h-3 w-3 animate-spin text-green-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {(agent.status === "provisioning" || agent.status === "connecting") && (
              <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {agent.status === "stopped"
              ? "Not connected"
              : agent.status === "provisioning"
                ? "Provisioning"
                : agent.status === "connecting"
                  ? "Connecting"
                  : agent.status === "failed"
                    ? "Failed"
                    : agent.status === "running" && agent.software_installing
                      ? "Running · Reinstalling software…"
                      : agent.status}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {agent.status === "running" ? (
            <button onClick={stopAgent} className={`${css.btn} text-red-500 ring-1 ring-red-200 hover:bg-red-50`}>
              Stop
            </button>
          ) : (
            <button onClick={startAgent} className={`${css.btn} text-green-600 ring-1 ring-green-200 hover:bg-green-50`}>
              Start
            </button>
          )}
        </div>
      </div>

      <div className="mb-6 flex border-b border-claude-border">
        {mainTabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setMainTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${mainTab === t.key
                ? "border-claude-accent text-claude-accent"
                : "border-transparent text-claude-text-muted hover:text-claude-text-secondary"
              }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {(agent.status === "provisioning" || agent.status === "connecting") && (mainTab === "workspace" || mainTab === "logs" || mainTab === "jobs") ? (
        <div className="rounded-xl border border-claude-border bg-claude-bg p-8 text-center">
          <div className="flex justify-center mb-4">
            <svg className="h-10 w-10 animate-spin text-claude-accent" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-claude-text-primary mb-1">
            {agent.status === "provisioning"
              ? "Provisioning workspace..."
              : "Connecting to agent..."}
          </p>
          <p className="text-xs text-claude-text-muted max-w-sm mx-auto">
            {agent.status === "provisioning"
              ? "Setting up the agent workspace and configuration files."
              : "Waiting for the agent to establish connection."}
          </p>
          {agent.status === "provisioning" && (
            <button
              onClick={refreshAgent}
              className="mt-4 text-xs text-claude-text-muted hover:text-claude-text-secondary underline"
            >
              Refresh status
            </button>
          )}
        </div>
      ) : agent.status !== "running" && (mainTab === "workspace" || mainTab === "logs" || mainTab === "jobs") ? (
        <div className="rounded-xl border border-claude-border bg-claude-bg p-8 text-center">
          <p className="text-sm font-medium text-claude-text-primary mb-1">Agent is not started</p>
          <p className="text-xs text-claude-text-muted mb-4 max-w-sm mx-auto">
            Start the agent to view workspace files, activity, logs, and scheduled jobs. Settings can be edited anytime.
          </p>
          <button onClick={startAgent} className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover`}>
            Start agent
          </button>
        </div>
      ) : (
        <>
          {mainTab === "workspace" && (
            <WorkspaceTab agentId={agentId!} token={token!} agentStatus={agent?.status} status_message={agent?.status_message} />
          )}
          {mainTab === "jobs" && <ScheduledJobsTab agentId={agentId!} />}
          {mainTab === "logs" && <LogsTab agentId={agentId!} token={token!} />}
        </>
      )}
      {mainTab === "settings" && agent && (
        <SettingsContent
          agentId={agentId!}
          agent={agent}
          update={update}
          updateTools={updateTools}
          setTools={setTools}
          updateSkills={updateSkills}
          updateChannel={updateChannel}
          onSave={save}
          onDeleted={onDeleted}
          dirty={dirty}
          saving={saving}
          saved={saved}
          isOffline={agent.status !== "running"}
          restartRequired={
            dirty &&
            !!lastSavedAgent &&
            JSON.stringify(agent.security?.docker) !== JSON.stringify(lastSavedAgent?.security?.docker)
          }
        />
      )}
    </PageContainer>
  );
}
