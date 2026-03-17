import { HEARTBEAT_SCHEDULE_OPTIONS, PROVIDER_DEFS } from "./constants";
import type { ActivityFilter, CronJobData, HeartbeatCfg, SkillsCfg, ToolsCfg, TreeNode } from "./types";
import { EVENT_TYPE_CONFIG } from "./constants";

export function deepMerge<T extends Record<string, unknown>>(base: T, patch: Record<string, unknown>): T {
  const out = { ...base } as Record<string, unknown>;
  for (const [k, v] of Object.entries(patch)) {
    if (v && typeof v === "object" && !Array.isArray(v) && typeof out[k] === "object" && out[k] && !Array.isArray(out[k])) {
      out[k] = deepMerge(out[k] as Record<string, unknown>, v as Record<string, unknown>);
    } else {
      out[k] = v;
    }
  }
  return out as T;
}

export function defaultTools(): ToolsCfg {
  return {
    web: { search: { provider: "duckduckgo", brave_api_key: "", serpapi_api_key: "", max_results: 5 } },
    exec: { timeout: 60, policy: { mode: "allow_all", allow: [], deny: [], relaxed: true } },
    restrict_to_workspace: false,
    ssrf_protection: true,
    mcp_servers: {},
  };
}

export function defaultSkills(): SkillsCfg {
  return { disabled: [] };
}

export function defaultHeartbeat(): HeartbeatCfg {
  return { enabled: true, interval_s: 1800, cron_expr: "", timezone: "" };
}

export function heartbeatScheduleToOption(interval_s: number): number {
  const match = HEARTBEAT_SCHEDULE_OPTIONS.find((o) => o.value === interval_s);
  if (match) return match.value;
  const closest = HEARTBEAT_SCHEDULE_OPTIONS.reduce((a, b) =>
    Math.abs(a.value - interval_s) <= Math.abs(b.value - interval_s) ? a : b
  );
  return closest.value;
}

export function detectProvider(model: string | undefined) {
  if (!model) return undefined;
  const lc = model.toLowerCase();
  return PROVIDER_DEFS.find((p) => p.keywords.some((kw) => lc.includes(kw)));
}

export function fmtPresetValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export function formatSchedule(s: CronJobData["schedule"]): string {
  if (s.kind === "cron" && s.expr) return s.expr;
  if (s.kind === "at" && s.atMs) return `at ${new Date(s.atMs).toLocaleString()}`;
  if (s.kind === "every" && s.everyMs) {
    const sec = Math.round(s.everyMs / 1000);
    if (sec < 60) return `every ${sec}s`;
    if (sec < 3600) return `every ${Math.round(sec / 60)}m`;
    return `every ${(sec / 3600).toFixed(1).replace(/\.0$/, "")}h`;
  }
  return s.kind;
}

export function relativeTime(ms: number | undefined): string {
  if (!ms) return "—";
  const diff = ms - Date.now();
  const absDiff = Math.abs(diff);
  const past = diff < 0;
  if (absDiff < 60_000) return past ? "just now" : "< 1m";
  if (absDiff < 3_600_000) { const m = Math.round(absDiff / 60_000); return past ? `${m}m ago` : `in ${m}m`; }
  if (absDiff < 86_400_000) { const h = Math.round(absDiff / 3_600_000); return past ? `${h}h ago` : `in ${h}h`; }
  const d = Math.round(absDiff / 86_400_000);
  return past ? `${d}d ago` : `in ${d}d`;
}

export function getEventConfig(eventType: string) {
  return EVENT_TYPE_CONFIG[eventType] ?? { label: eventType, color: "text-claude-text-tertiary", bg: "bg-claude-surface border-claude-border", icon: "•", group: "all" as ActivityFilter };
}

export function formatActivityTime(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  } catch {
    return iso;
  }
}

export function triggerDownload(url: string, fallbackName: string) {
  const token = localStorage.getItem("token");
  fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
    .then((res) => {
      if (!res.ok) throw new Error(`Download failed: ${res.status}`);
      const cd = res.headers.get("Content-Disposition") ?? "";
      const match = cd.match(/filename="?([^"]+)"?/);
      const name = match?.[1] ?? fallbackName;
      return res.blob().then((blob) => ({ blob, name }));
    })
    .then(({ blob, name }) => {
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    })
    .catch((err) => console.error("Download failed:", err));
}

export function buildTree(paths: string[], rootDirs: string[] = []): TreeNode[] {
  const root: TreeNode = { name: "", path: "", isDir: true, children: [] };

  function ensureDir(node: TreeNode, name: string, dirPath: string): TreeNode {
    let child = node.children.find((c) => c.name === name && c.isDir);
    if (!child) {
      child = { name, path: dirPath, isDir: true, children: [] };
      node.children.push(child);
    }
    return child;
  }

  for (const dir of rootDirs) {
    ensureDir(root, dir, dir);
  }

  for (const p of paths) {
    const parts = p.split("/");
    let node = root;
    for (let i = 0; i < parts.length; i++) {
      const isLast = i === parts.length - 1;
      const segPath = parts.slice(0, i + 1).join("/");
      if (isLast) {
        let child = node.children.find((c) => c.name === parts[i] && !c.isDir);
        if (!child) {
          child = { name: parts[i], path: p, isDir: false, children: [] };
          node.children.push(child);
        }
      } else {
        node = ensureDir(node, parts[i], segPath);
      }
    }
  }

  function sortTree(nodes: TreeNode[]) {
    nodes.sort((a, b) => {
      const aDir = a.isDir ? 0 : 1;
      const bDir = b.isDir ? 0 : 1;
      if (aDir !== bDir) return aDir - bDir;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach((n) => sortTree(n.children));
  }
  sortTree(root.children);
  return root.children;
}
