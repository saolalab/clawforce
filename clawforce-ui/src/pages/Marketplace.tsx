import { useState, useEffect } from "react";
import { PageContainer, PageHeader } from "../components/ui";
import { useTemplates, useSearchSkills, useSearchMcpServers, useSoftwareCatalog } from "../lib/queries";
import CreateClawModal from "../components/CreateClawModal";
import TemplateDetailModal from "../components/TemplateDetailModal";
import InstallSkillModal from "../components/InstallSkillModal";
import InstallMcpModal from "../components/InstallMcpModal";
import InstallSoftwareModal from "../components/InstallSoftwareModal";
import type { MarketplaceSkill, MCPRegistryServer, SoftwareCatalogEntry } from "../lib/types";
import {
  HiOutlineCommandLine,
  HiOutlineCodeBracket,
  HiOutlineServerStack,
  HiOutlinePresentationChartBar,
  HiOutlineBanknotes,
  HiOutlineUserGroup,
  HiOutlineMegaphone,
  HiOutlineScale,
  HiOutlineChartBar,
  HiOutlineSparkles,
  HiOutlineTrophy,
} from "react-icons/hi2";

type Tab = "templates" | "skills" | "mcp" | "software";

const css = {
  input: "w-full rounded-lg border border-claude-border bg-white px-3 py-2 text-sm placeholder:text-claude-text-muted focus:border-claude-accent focus:outline-none focus:ring-1 focus:ring-claude-accent/30 transition-colors",
  btn: "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
};

const TAB_FROM_HASH: Record<string, Tab> = {
  templates: "templates",
  skills: "skills",
  mcp: "mcp",
  software: "software",
};

export default function Marketplace() {
  const [tab, setTab] = useState<Tab>(() => {
    const hash = typeof window !== "undefined" ? window.location.hash.slice(1) : "";
    return TAB_FROM_HASH[hash] ?? "templates";
  });
  const { data: templates = [], isLoading: templatesLoading } = useTemplates();

  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.slice(1);
      if (TAB_FROM_HASH[hash]) setTab(TAB_FROM_HASH[hash]);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (window.location.hash.slice(1) !== tab) {
      window.location.hash = tab;
    }
  }, [tab]);

  const tabClass = (t: Tab) =>
    `px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
      tab === t
        ? "bg-white text-claude-text-primary shadow-sm"
        : "text-claude-text-muted hover:text-claude-text-secondary"
    }`;

  return (
    <PageContainer>
      <PageHeader title="Marketplace" description="Browse templates, skills, MCP servers, and software" />

      <div className="flex rounded-lg border border-claude-border bg-claude-surface p-0.5 w-fit mb-6">
        <button className={tabClass("templates")} onClick={() => setTab("templates")}>
          Claw Templates
        </button>
        <button className={tabClass("skills")} onClick={() => setTab("skills")}>
          Skills
        </button>
        <button className={tabClass("mcp")} onClick={() => setTab("mcp")}>
          MCP Servers
        </button>
        <button className={tabClass("software")} onClick={() => setTab("software")}>
          Software
        </button>
      </div>

      {tab === "templates" && (
        <TemplatesTab templates={templates} isLoading={templatesLoading} />
      )}

      {tab === "skills" && <SkillsTab />}

      {tab === "mcp" && <McpTab />}

      {tab === "software" && <SoftwareTab />}
    </PageContainer>
  );
}

function TemplatesTab({ templates, isLoading }: { templates: { value: string; label: string }[]; isLoading: boolean }) {
  const [detailTemplate, setDetailTemplate] = useState<string | null>(null);
  const [createTemplate, setCreateTemplate] = useState<string | null>(null);

  if (isLoading) {
    return <p className="text-claude-text-muted text-sm">Loading templates...</p>;
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {templates.map((t) => (
          <button
            key={t.value}
            onClick={() => setDetailTemplate(t.value)}
            className="rounded-xl border border-claude-border bg-white p-4 hover:border-claude-accent/50 hover:shadow-sm transition-all text-left group"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-claude-accent/10 group-hover:bg-claude-accent/20 transition-colors">
                <RoleIcon role={t.value} />
              </div>
              <div>
                <h3 className="font-medium text-claude-text-primary">{t.label}</h3>
              </div>
            </div>
            <p className="text-sm text-claude-text-secondary">
              Pre-configured with {t.label.toLowerCase()} skills and settings.
            </p>
            <div className="mt-3 flex justify-end">
              <span className="text-xs text-claude-accent opacity-0 group-hover:opacity-100 transition-opacity font-medium">
                Create Claw →
              </span>
            </div>
          </button>
        ))}
      </div>

      <TemplateDetailModal
        open={!!detailTemplate}
        templateId={detailTemplate}
        onClose={() => setDetailTemplate(null)}
        onCreateClaw={(id) => setCreateTemplate(id)}
      />

      <CreateClawModal
        open={!!createTemplate}
        onClose={() => setCreateTemplate(null)}
        initialTemplate={createTemplate ?? undefined}
      />
    </>
  );
}

function SkillsTab() {
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const { data: skills, isLoading, error } = useSearchSkills(searchQuery, true);
  const [installSkill, setInstallSkill] = useState<MarketplaceSkill | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<MarketplaceSkill | null>(null);

  useEffect(() => {
    setSearchQuery("");
  }, []);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearchQuery(searchInput.trim() || "");
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-claude-text-secondary max-w-2xl">
        <span>Skills extend your claws with specialized capabilities. Powered by</span>
        <a
          href="https://agentskill.sh"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-claude-accent hover:underline font-medium"
        >
          agentskill.sh
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 max-w-2xl">
        <div className="relative flex-1">
          <svg className="absolute left-2.5 top-2.5 h-4 w-4 text-claude-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            className={`${css.input} pl-8`}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search skills... (e.g. web scraping, calendar, github)"
          />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover disabled:opacity-40 shrink-0 min-w-[80px]`}
        >
          {isLoading ? (
            <span className="inline-flex items-center gap-1">
              <span className="h-1 w-1 rounded-full bg-white animate-pulse" />
              <span className="h-1 w-1 rounded-full bg-white animate-pulse [animation-delay:150ms]" />
              <span className="h-1 w-1 rounded-full bg-white animate-pulse [animation-delay:300ms]" />
            </span>
          ) : "Search"}
        </button>
      </form>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          Search failed: {error instanceof Error ? error.message : "Unknown error"}
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-2 text-sm text-claude-text-muted">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Searching skills...
          </div>
        </div>
      )}

      {!isLoading && skills && skills.length > 0 && (
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {skills.map((skill: MarketplaceSkill) => (
              <SkillCard
                key={skill.slug}
                skill={skill}
                onSelect={() => setSelectedSkill(skill)}
                onInstall={() => setInstallSkill(skill)}
              />
            ))}
          </div>
        </div>
      )}

      {!isLoading && skills && skills.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-claude-text-muted">
          <svg className="h-8 w-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm">
            {searchQuery
              ? `No skills found for "${searchQuery}"`
              : "No skills found in agentskill.sh registry."}
          </p>
          <p className="text-xs mt-1">
            Try different keywords or browse{" "}
            <a
              href="https://agentskill.sh"
              target="_blank"
              rel="noreferrer"
              className="text-claude-accent hover:underline"
            >
              agentskill.sh
            </a>
          </p>
        </div>
      )}

      <InstallSkillModal
        open={!!installSkill}
        onClose={() => setInstallSkill(null)}
        skill={installSkill}
      />

      <SkillDetailModal
        skill={selectedSkill}
        onClose={() => setSelectedSkill(null)}
        onInstall={() => {
          setSelectedSkill(null);
          if (selectedSkill) setInstallSkill(selectedSkill);
        }}
      />
    </div>
  );
}

function isLikelyAuthor(value: string | undefined): boolean {
  if (!value) return false;
  if (/^\d+\.?\d*$/.test(value)) return false;
  if (/^v?\d+(\.\d+)*$/.test(value)) return false;
  if (value.length > 40) return false;
  if ((value.match(/\s/g) || []).length > 3) return false;
  return true;
}

function isLikelyVersion(value: string | undefined): boolean {
  return !!value && /^v?\d+(\.\d+)*$/.test(value);
}

function SkillCard({
  skill,
  onSelect,
  onInstall,
}: {
  skill: MarketplaceSkill;
  onSelect: () => void;
  onInstall: () => void;
}) {
  const author = isLikelyAuthor(skill.author) ? skill.author : undefined;
  const descFromAuthor = !isLikelyAuthor(skill.author) && skill.author && !isLikelyVersion(skill.author) ? skill.author : undefined;
  const description = (skill.description && !isLikelyVersion(skill.description)) ? skill.description : descFromAuthor;
  const version = skill.version || (isLikelyVersion(skill.description) ? skill.description?.replace(/^v/, "") : undefined);

  return (
    <div className="rounded-xl border border-claude-border bg-white p-4 hover:border-claude-accent/30 transition-colors flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <button onClick={onSelect} className="flex items-center gap-3 min-w-0 text-left">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 shrink-0">
            <svg className="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
            </svg>
          </div>
          <div className="min-w-0">
            <span className="text-sm font-medium text-claude-text-primary">{skill.name}</span>
            {author && (
              <p className="text-[10px] text-claude-text-muted mt-0.5">by {author}</p>
            )}
          </div>
        </button>
      </div>
      <button onClick={onSelect} className="text-left w-full">
        {description && (
          <p className="mt-2 text-xs text-claude-text-secondary line-clamp-2">{description}</p>
        )}
      </button>
      <div className="mt-auto pt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {version && (
            <span className="rounded px-1.5 py-px text-[10px] font-mono text-claude-text-muted ring-1 ring-claude-border">
              v{version}
            </span>
          )}
        </div>
        <div className="flex-1" />
        <button
          onClick={onInstall}
          className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover text-xs px-3 py-1.5`}
        >
          Install
        </button>
      </div>
    </div>
  );
}

function McpTab() {
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const { data: servers, isLoading, error } = useSearchMcpServers(searchQuery);
  const [selectedServer, setSelectedServer] = useState<MCPRegistryServer | null>(null);
  const [installServer, setInstallServer] = useState<MCPRegistryServer | null>(null);

  const sortedServers = servers
    ? [...servers].sort((a, b) => (b.downloads || 0) - (a.downloads || 0))
    : [];

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearchQuery(searchInput.trim());
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-claude-text-secondary max-w-2xl">
        <span>MCP servers extend your claws with external tools. Powered by</span>
        <a
          href="https://registry.modelcontextprotocol.io"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-claude-accent hover:underline font-medium"
        >
          registry.modelcontextprotocol.io
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 max-w-2xl">
        <div className="relative flex-1">
          <svg className="absolute left-2.5 top-2.5 h-4 w-4 text-claude-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            className={`${css.input} pl-8`}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search MCP servers... (e.g. filesystem, github, postgres)"
          />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover disabled:opacity-40 shrink-0 min-w-[80px]`}
        >
          {isLoading ? (
            <span className="inline-flex items-center gap-1">
              <span className="h-1 w-1 rounded-full bg-white animate-pulse" />
              <span className="h-1 w-1 rounded-full bg-white animate-pulse [animation-delay:150ms]" />
              <span className="h-1 w-1 rounded-full bg-white animate-pulse [animation-delay:300ms]" />
            </span>
          ) : "Search"}
        </button>
      </form>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          Search failed: {error instanceof Error ? error.message : "Unknown error"}
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-2 text-sm text-claude-text-muted">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Searching MCP registry...
          </div>
        </div>
      )}

      {!isLoading && sortedServers.length > 0 && (() => {
        const displayServers = sortedServers.slice(0, Math.floor(sortedServers.length / 3) * 3);
        return (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {displayServers.map((server: MCPRegistryServer) => {
                const serverId = server.id || server.slug;
                return (
                  <McpServerCard
                    key={serverId}
                    server={server}
                    onSelect={() => setSelectedServer(server)}
                    onInstall={() => setInstallServer(server)}
                  />
                );
              })}
            </div>
          </div>
        );
      })()}

      {!isLoading && sortedServers.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-claude-text-muted">
          <svg className="h-8 w-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm">
            {searchQuery
              ? `No MCP servers found for "${searchQuery}"`
              : "No MCP servers available."}
          </p>
          <p className="text-xs mt-1">
            Try different keywords or browse{" "}
            <a
              href="https://registry.modelcontextprotocol.io"
              target="_blank"
              rel="noreferrer"
              className="text-claude-accent hover:underline"
            >
              registry.modelcontextprotocol.io
            </a>
          </p>
        </div>
      )}

      <McpServerDetailModal
        server={selectedServer}
        onClose={() => setSelectedServer(null)}
        onInstall={() => {
          setInstallServer(selectedServer);
          setSelectedServer(null);
        }}
      />

      <InstallMcpModal
        open={!!installServer}
        onClose={() => setInstallServer(null)}
        server={installServer}
      />
    </div>
  );
}

function formatDownloads(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function McpServerCard({
  server,
  onSelect,
  onInstall,
}: {
  server: MCPRegistryServer;
  onSelect: () => void;
  onInstall: () => void;
}) {
  const isVerified = server.verified || server.is_verified;
  const downloads = server.downloads || 0;
  return (
    <div className="rounded-xl border border-claude-border bg-white p-4 hover:border-claude-accent/30 transition-colors flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <button onClick={onSelect} className="flex items-center gap-3 min-w-0 text-left">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/20 to-indigo-500/20 shrink-0">
            <svg className="h-5 w-5 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
            </svg>
          </div>
          <div className="min-w-0">
            <span className="text-sm font-medium text-claude-text-primary">{server.name}</span>
            {server.author && !/^\d+\.?\d*$/.test(server.author) && (
              <p className="text-[10px] text-claude-text-muted mt-0.5">by {server.author}</p>
            )}
          </div>
        </button>
        {downloads > 0 && (
          <span className="inline-flex items-center gap-1 text-[10px] text-claude-text-muted shrink-0" title={`${downloads.toLocaleString()} downloads`}>
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {formatDownloads(downloads)}
          </span>
        )}
      </div>
      <button onClick={onSelect} className="text-left w-full">
        <p className="mt-2 text-xs text-claude-text-secondary line-clamp-2">{server.description}</p>
      </button>
      <div className="mt-auto pt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {server.version && (
            <span className="rounded px-1.5 py-px text-[10px] font-mono text-claude-text-muted ring-1 ring-claude-border">
              v{server.version}
            </span>
          )}
          {isVerified && (
            <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-px text-[10px] font-medium bg-green-50 text-green-700 ring-1 ring-green-200">
              <svg className="h-2.5 w-2.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Verified
            </span>
          )}
        </div>
        <div className="flex-1" />
        <button
          onClick={onInstall}
          className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover text-xs px-3 py-1.5`}
        >
          Install
        </button>
      </div>
    </div>
  );
}

function McpServerDetailModal({
  server,
  onClose,
  onInstall,
}: {
  server: MCPRegistryServer | null;
  onClose: () => void;
  onInstall: () => void;
}) {
  if (!server) return null;

  const isVerified = server.verified || server.is_verified;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-claude-border flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/20 to-indigo-500/20 shrink-0">
              <svg className="h-4 w-4 text-violet-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
              </svg>
            </div>
            <h2 className="text-base font-semibold text-claude-text-primary truncate">{server.name}</h2>
            {isVerified && (
              <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-px text-[10px] font-medium bg-green-50 text-green-700 ring-1 ring-green-200 shrink-0">
                <svg className="h-2.5 w-2.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Verified
              </span>
            )}
            {server.version && (
              <span className="text-[10px] font-mono text-claude-text-muted shrink-0">v{server.version}</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-claude-surface transition-colors shrink-0"
          >
            <svg className="h-4 w-4 text-claude-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          <p className="text-sm text-claude-text-secondary">{server.description}</p>

          {server.categories && server.categories.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-claude-text-muted uppercase tracking-wide mb-2">Categories</h3>
              <div className="flex flex-wrap gap-2">
                {server.categories.map((cat) => (
                  <span
                    key={cat}
                    className="rounded-full px-3 py-1 text-xs bg-claude-surface text-claude-text-secondary"
                  >
                    {cat}
                  </span>
                ))}
              </div>
            </div>
          )}

          {server.capabilities && server.capabilities.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-claude-text-muted uppercase tracking-wide mb-2">Capabilities</h3>
              <div className="flex flex-wrap gap-2">
                {server.capabilities.map((cap) => (
                  <span
                    key={cap}
                    className="rounded px-2 py-1 text-xs bg-green-50 text-green-700 ring-1 ring-green-200"
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-4 text-sm">
            {server.repository && (
              <a
                href={server.repository}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-claude-text-secondary hover:text-claude-accent transition-colors"
              >
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                Repository
              </a>
            )}
            {server.homepage && (
              <a
                href={server.homepage}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-claude-text-secondary hover:text-claude-accent transition-colors"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
                Homepage
              </a>
            )}
            {server.license && (
              <span className="inline-flex items-center gap-1.5 text-claude-text-muted">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                {server.license}
              </span>
            )}
            {server.downloads > 0 && (
              <span className="inline-flex items-center gap-1.5 text-claude-text-muted">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                {server.downloads.toLocaleString()} installs
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 text-sm">
            <span className="text-claude-text-muted">Server ID:</span>
            <code className="rounded bg-slate-900 text-slate-100 px-2 py-1 text-xs font-mono">
              {server.id || server.slug}
            </code>
          </div>
        </div>

        <div className="px-4 py-2 border-t border-claude-border bg-claude-surface/30 flex justify-end gap-2">
          <button
            onClick={onClose}
            className={`${css.btn} border border-claude-border bg-white hover:bg-claude-surface text-xs px-3 py-1.5`}
          >
            Close
          </button>
          <button
            onClick={onInstall}
            className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover text-xs px-3 py-1.5`}
          >
            Install
          </button>
        </div>
      </div>
    </div>
  );
}

function SkillDetailModal({
  skill,
  onClose,
  onInstall,
}: {
  skill: MarketplaceSkill | null;
  onClose: () => void;
  onInstall: () => void;
}) {
  if (!skill) return null;

  const author = isLikelyAuthor(skill.author) ? skill.author : undefined;
  const descFromAuthor = !isLikelyAuthor(skill.author) && skill.author && !isLikelyVersion(skill.author) ? skill.author : undefined;
  const description = (skill.description && !isLikelyVersion(skill.description)) ? skill.description : descFromAuthor;
  const version = skill.version || (isLikelyVersion(skill.description) ? skill.description?.replace(/^v/, "") : undefined);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-claude-border flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 shrink-0">
              <svg className="h-4 w-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
              </svg>
            </div>
            <h2 className="text-base font-semibold text-claude-text-primary truncate">{skill.name}</h2>
            {version && (
              <span className="text-[10px] font-mono text-claude-text-muted shrink-0">v{version}</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-claude-surface transition-colors shrink-0"
          >
            <svg className="h-4 w-4 text-claude-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {description && (
            <p className="text-sm text-claude-text-secondary">{description}</p>
          )}

          {author && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-claude-text-muted">Author:</span>
              <span className="text-claude-text-primary">{author}</span>
            </div>
          )}

          <div className="flex items-center gap-2 text-sm">
            <span className="text-claude-text-muted">Skill ID:</span>
            <code className="rounded bg-slate-900 text-slate-100 px-2 py-1 text-xs font-mono">
              {skill.slug}
            </code>
          </div>
        </div>

        <div className="px-4 py-2 border-t border-claude-border bg-claude-surface/30 flex justify-end gap-2">
          <button
            onClick={onClose}
            className={`${css.btn} border border-claude-border bg-white hover:bg-claude-surface text-xs px-3 py-1.5`}
          >
            Close
          </button>
          <button
            onClick={onInstall}
            className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover text-xs px-3 py-1.5`}
          >
            Install
          </button>
        </div>
      </div>
    </div>
  );
}

function SoftwareTab() {
  const { data: catalog = [], isLoading } = useSoftwareCatalog();
  const [installEntry, setInstallEntry] = useState<SoftwareCatalogEntry | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-claude-text-secondary max-w-2xl">
        <span>Software extends your claws with CLI tools that can be installed into Docker containers.</span>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-2 text-sm text-claude-text-muted">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading software catalog...
          </div>
        </div>
      )}

      {!isLoading && catalog.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {catalog.map((entry: SoftwareCatalogEntry) => (
            <SoftwareCard
              key={entry.id}
              entry={entry}
              onInstall={() => setInstallEntry(entry)}
            />
          ))}
        </div>
      )}

      {!isLoading && catalog.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-claude-text-muted">
          <svg className="h-8 w-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm">No software available in the catalog yet.</p>
        </div>
      )}

      <InstallSoftwareModal
        open={!!installEntry}
        onClose={() => setInstallEntry(null)}
        entry={installEntry}
      />
    </div>
  );
}

function SoftwareCard({
  entry,
  onInstall,
}: {
  entry: SoftwareCatalogEntry;
  onInstall: () => void;
}) {
  return (
    <div className="rounded-xl border border-claude-border bg-white p-4 hover:border-claude-accent/30 transition-colors flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500/20 to-teal-500/20 shrink-0">
            <svg className="h-5 w-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
            </svg>
          </div>
          <div className="min-w-0">
            <span className="text-sm font-medium text-claude-text-primary">{entry.name}</span>
            {entry.author && (
              <p className="text-[10px] text-claude-text-muted mt-0.5">by {entry.author}</p>
            )}
          </div>
        </div>
      </div>
      {entry.description && (
        <p className="mt-2 text-xs text-claude-text-secondary line-clamp-2">{entry.description}</p>
      )}
      <div className="mt-auto pt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {entry.version && (
            <span className="rounded px-1.5 py-px text-[10px] font-mono text-claude-text-muted ring-1 ring-claude-border">
              v{entry.version}
            </span>
          )}
          {entry.categories && entry.categories.length > 0 && (
            <span className="rounded px-1.5 py-px text-[10px] text-claude-text-muted ring-1 ring-claude-border">
              {entry.categories[0]}
            </span>
          )}
        </div>
        <div className="flex-1" />
        <button
          onClick={onInstall}
          className={`${css.btn} bg-claude-accent text-white hover:bg-claude-accent-hover text-xs px-3 py-1.5`}
        >
          Install
        </button>
      </div>
    </div>
  );
}

function RoleIcon({ role }: { role: string }) {
  const cls = "h-5 w-5 text-claude-accent";
  const icons: Record<string, React.ReactNode> = {
    ceo: <HiOutlineTrophy className={cls} />,
    cto: <HiOutlineCommandLine className={cls} />,
    sre: <HiOutlineServerStack className={cls} />,
    "software-engineer": <HiOutlineCodeBracket className={cls} />,
    "product-manager": <HiOutlinePresentationChartBar className={cls} />,
    "finance-controller": <HiOutlineBanknotes className={cls} />,
    "hr-manager": <HiOutlineUserGroup className={cls} />,
    "marketing-lead": <HiOutlineMegaphone className={cls} />,
    "legal-counsel": <HiOutlineScale className={cls} />,
    "data-analyst": <HiOutlineChartBar className={cls} />,
  };
  return <>{icons[role] || <HiOutlineSparkles className={cls} />}</>;
}
