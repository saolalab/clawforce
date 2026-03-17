import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import { useWorkspaceFiles, useWorkspaceFile, useSaveWorkspaceFile, useDeleteWorkspaceFile, useRenameWorkspaceFile, useMoveWorkspaceFile } from "../../../lib/queries";
import { api } from "../../../lib/api";
import ConfirmDialog from "../../ConfirmDialog";
import { buildTree, triggerDownload } from "../utils";
import { FileIcon } from "../ui/Icons";
import { TreeItem } from "./TreeItem";
import { MarkdownPreview } from "./MarkdownPreview";
import { TerminalPanel } from "./TerminalPanel";
import type { WsViewMode } from "../types";

export function WorkspaceTab({
  agentId,
  token,
  agentStatus,
  status_message,
}: {
  agentId: string;
  token: string;
  agentStatus?: string;
  status_message?: string;
}) {
  const { data: wsData, isLoading: wsLoading } = useWorkspaceFiles(agentId, "workspace");
  const { data: profData, isLoading: profLoading } = useWorkspaceFiles(agentId, "profiles");
  const wsFiles = (wsData?.files ?? []).map((f: string) => `workspace/${f}`);
  const profFiles = (profData?.files ?? []).map((f: string) => `profiles/${f}`);
  const files = [...wsFiles, ...profFiles];
  const [current, setCurrent] = useState("");
  const { data: fileContent } = useWorkspaceFile(agentId, current);
  const [content, setContent] = useState("");
  const [wsDirty, setWsDirty] = useState(false);
  const saveMut = useSaveWorkspaceFile(agentId);
  const deleteMut = useDeleteWorkspaceFile(agentId);
  const renameMut = useRenameWorkspaceFile(agentId);
  const moveMut = useMoveWorkspaceFile(agentId);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(["workspace", "profiles"]));
  const [viewMode, setViewMode] = useState<WsViewMode>("preview");
  const [terminalOpen, setTerminalOpen] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [renameTarget, setRenameTarget] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [moveTarget, setMoveTarget] = useState<string | null>(null);
  const [moveDestValue, setMoveDestValue] = useState("");
  const [explorerWidth, setExplorerWidth] = useState(224);
  const [isResizing, setIsResizing] = useState(false);

  const MIN_EXPLORER = 160;
  const MAX_EXPLORER = 480;

  function startResize() {
    setIsResizing(true);
  }

  useEffect(() => {
    if (!isResizing) return;
    function onMove(e: MouseEvent) {
      const x = e.clientX;
      const container = document.querySelector("[data-workspace-container]");
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const relX = x - rect.left;
      const clamped = Math.max(MIN_EXPLORER, Math.min(MAX_EXPLORER, relX));
      setExplorerWidth(clamped);
    }
    function onUp() {
      setIsResizing(false);
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing]);

  const isLoading = wsLoading || profLoading;
  const isEmpty = !isLoading && files.length === 0;
  const isProvisioning = agentStatus === "provisioning" || agentStatus === "connecting";
  const isMarkdown = current.endsWith(".md");
  const isAgentReadOnly = current.startsWith("profiles/");

  const tree = buildTree(files, ["workspace", "profiles"]);

  useEffect(() => {
    if (!current && files.length > 0) {
      const defaultFile =
        profFiles.find((f: string) => f.endsWith("AGENTS.md")) ||
        profFiles.find((f: string) => f.endsWith(".md")) ||
        wsFiles.find((f: string) => f.endsWith("README.md")) ||
        wsFiles.find((f: string) => f.endsWith(".md")) ||
        files[0];
      if (defaultFile) setCurrent(defaultFile);
    }
  }, [files, current, profFiles, wsFiles]);

  useEffect(() => {
    if (fileContent !== undefined) {
      setContent(fileContent);
      setWsDirty(false);
    }
  }, [fileContent]);

  useEffect(() => {
    setViewMode(current.endsWith(".md") ? "preview" : "edit");
  }, [current]);

  function toggleExpand(path: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(path) ? next.delete(path) : next.add(path);
      return next;
    });
  }

  function handleSave() {
    saveMut.mutate({ path: current, content }, { onSuccess: () => setWsDirty(false) });
  }

  function handleDelete(path: string) {
    setDeleteTarget(path);
  }

  function confirmDelete() {
    if (!deleteTarget) return;
    deleteMut.mutate(deleteTarget, {
      onSuccess: () => {
        if (current === deleteTarget || current.startsWith(deleteTarget + "/")) {
          setCurrent("");
        }
        setDeleteTarget(null);
      },
      onError: () => setDeleteTarget(null),
    });
  }

  function handleRename(path: string) {
    setRenameTarget(path);
    setRenameValue(path.split("/").pop() || "");
  }

  function confirmRename() {
    if (!renameTarget || !renameValue.trim()) return;
    renameMut.mutate(
      { path: renameTarget, newName: renameValue.trim() },
      {
        onSuccess: () => {
          if (current === renameTarget) {
            const parentPath = renameTarget.substring(0, renameTarget.lastIndexOf("/"));
            setCurrent(parentPath ? `${parentPath}/${renameValue.trim()}` : renameValue.trim());
          }
          setRenameTarget(null);
          setRenameValue("");
        },
        onError: () => {
          setRenameTarget(null);
          setRenameValue("");
        },
      }
    );
  }

  function handleMove(path: string) {
    setMoveTarget(path);
    setMoveDestValue(path);
  }

  function confirmMove() {
    if (!moveTarget || !moveDestValue.trim()) return;
    moveMut.mutate(
      { srcPath: moveTarget, destPath: moveDestValue.trim() },
      {
        onSuccess: () => {
          if (current === moveTarget) {
            setCurrent(moveDestValue.trim());
          }
          setMoveTarget(null);
          setMoveDestValue("");
        },
        onError: () => {
          setMoveTarget(null);
          setMoveDestValue("");
        },
      }
    );
  }

  const lang = current.endsWith(".md") ? "markdown" : current.endsWith(".json") ? "json" : current.endsWith(".sh") ? "shell" : current.endsWith(".yaml") || current.endsWith(".yml") ? "yaml" : "plaintext";

  return (
    <div data-workspace-container className="flex h-[calc(100vh-14rem)] gap-0 rounded-xl border border-claude-border overflow-hidden bg-white">
      {/* Explorer sidebar */}
      <div
        className="flex-shrink-0 border-r border-claude-border bg-claude-bg flex flex-col"
        style={{ width: explorerWidth }}
      >
        <div className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-claude-text-muted">
          Explorer
        </div>
        <div className="flex-1 overflow-y-auto px-1 pb-2">
          {isLoading ? (
            <div className="flex flex-col gap-2 p-2">
              <div className="h-5 w-24 animate-pulse rounded bg-claude-border/50" />
              <div className="ml-4 h-4 w-32 animate-pulse rounded bg-claude-border/30" />
              <div className="ml-4 h-4 w-28 animate-pulse rounded bg-claude-border/30" />
              <div className="h-5 w-20 animate-pulse rounded bg-claude-border/50 mt-2" />
              <div className="ml-4 h-4 w-36 animate-pulse rounded bg-claude-border/30" />
            </div>
          ) : isEmpty ? (
            <div className="p-3 text-xs text-claude-text-muted">
              <p className="mb-2">No files yet.</p>
              <p className="text-[11px] leading-relaxed">
                {isProvisioning
                  ? "Files will appear once the agent has finished provisioning and connecting."
                  : "Files will appear once the agent has finished connecting."}
              </p>
            </div>
          ) : (
            tree.map((node) => (
              <TreeItem
                key={node.path}
                node={node}
                depth={0}
                current={current}
                onSelect={setCurrent}
                expanded={expanded}
                toggleExpand={toggleExpand}
                agentId={agentId}
                onDelete={handleDelete}
                onRename={handleRename}
                onMove={handleMove}
              />
            ))
          )}
        </div>
        <div className="flex-shrink-0 border-t border-claude-border p-1.5">
          <button
            type="button"
            onClick={() => setTerminalOpen((o) => !o)}
            className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-[11px] font-medium transition-colors ${terminalOpen
                ? "bg-claude-accent/10 text-claude-accent"
                : "text-claude-text-muted hover:bg-claude-sidebar-hover hover:text-claude-text-secondary"
              }`}
            title={terminalOpen ? "Close terminal" : "Open terminal"}
          >
            <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 12h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2z" />
            </svg>
            Terminal
          </button>
        </div>
      </div>

      {/* Resizable divider */}
      <div
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={explorerWidth}
        aria-valuemin={MIN_EXPLORER}
        aria-valuemax={MAX_EXPLORER}
        onMouseDown={startResize}
        className={`flex-shrink-0 w-px cursor-col-resize select-none transition-colors hover:bg-claude-accent/20 flex items-center justify-center group ${isResizing ? "bg-claude-accent/30" : "bg-claude-border"}`}
      >
        <div className="w-0.5 h-8 rounded-full bg-claude-border group-hover:bg-claude-accent/60 transition-colors" />
      </div>

      {/* Editor / Preview pane + optional terminal */}
      <div className="flex flex-1 flex-col min-h-0 overflow-hidden">
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {current ? (
            <>
              <div className="flex items-center justify-between border-b border-claude-border bg-claude-surface px-3 py-2">
                <div className="flex items-center gap-1.5 min-w-0">
                  <FileIcon name={current.split("/").pop()!} />
                  <span className="truncate font-mono text-[11px] text-claude-text-secondary">{current}</span>
                  {isAgentReadOnly && (
                    <span className="shrink-0 rounded bg-amber-50 ring-1 ring-amber-200 px-1.5 py-0.5 text-[10px] text-amber-600" title="The agent cannot modify this file at runtime">
                      agent r/o
                    </span>
                  )}
                  {wsDirty && <span className="ml-1 h-1.5 w-1.5 rounded-full bg-claude-accent shrink-0" />}
                </div>
                <div className="flex items-center gap-1.5">
                  {isMarkdown && (
                    <div className="flex rounded-md border border-claude-border bg-white p-0.5">
                      <button
                        type="button"
                        onClick={() => setViewMode("edit")}
                        className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${viewMode === "edit"
                            ? "bg-claude-accent/10 text-claude-accent"
                            : "text-claude-text-muted hover:text-claude-text-secondary"
                          }`}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => setViewMode("preview")}
                        className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${viewMode === "preview"
                            ? "bg-claude-accent/10 text-claude-accent"
                            : "text-claude-text-muted hover:text-claude-text-secondary"
                          }`}
                      >
                        Preview
                      </button>
                    </div>
                  )}
                  <button
                    onClick={handleSave}
                    disabled={!wsDirty || saveMut.isPending}
                    className={`shrink-0 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${saveMut.isPending
                        ? "bg-claude-surface text-claude-text-muted"
                        : wsDirty
                          ? "bg-claude-accent text-white hover:bg-claude-accent-hover"
                          : "bg-claude-surface text-claude-text-muted cursor-not-allowed"
                      }`}
                  >
                    {saveMut.isPending ? "Saving…" : "Save"}
                  </button>
                  <button
                    type="button"
                    onClick={() => triggerDownload(
                      api.agents.downloadFileUrl(agentId, current),
                      current.split("/").pop() ?? "file",
                    )}
                    className="shrink-0 rounded-md px-2.5 py-1 text-xs font-medium text-claude-text-muted hover:text-claude-text-secondary hover:bg-claude-surface transition-colors"
                    title="Download file"
                  >
                    <svg className="h-4 w-4 inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => setExplorerWidth((w) => (w >= MAX_EXPLORER ? 224 : MAX_EXPLORER))}
                    className={`shrink-0 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${explorerWidth >= MAX_EXPLORER
                        ? "bg-claude-accent/10 text-claude-accent"
                        : "text-claude-text-muted hover:text-claude-text-secondary hover:bg-claude-surface"
                      }`}
                    title={explorerWidth >= MAX_EXPLORER ? "Collapse explorer" : "Expand explorer"}
                  >
                    <svg className="h-4 w-4 inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
                    </svg>
                  </button>
                </div>
              </div>
              {isMarkdown && viewMode === "preview" ? (
                <MarkdownPreview content={content} />
              ) : (
                <Editor
                  height="100%"
                  language={lang}
                  value={content}
                  onChange={(v) => {
                    setContent(v ?? "");
                    setWsDirty(true);
                  }}
                  theme="light"
                  options={{
                    fontSize: 13,
                    minimap: { enabled: false },
                    padding: { top: 12 },
                    wordWrap: "on",
                  }}
                />
              )}
            </>
          ) : (
            <div className="flex h-full flex-col items-center justify-center text-claude-text-muted text-sm gap-3 p-8">
              {isLoading ? (
                <>
                  <svg className="h-8 w-8 animate-spin text-claude-accent/50" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span>Loading workspace...</span>
                </>
              ) : isEmpty ? (
                <>
                  {isProvisioning ? (
                    <div className="flex flex-col items-center gap-6 max-w-md">
                      {(() => {
                        const isProvisioningPhase = agentStatus === "provisioning";
                        const phases = [
                          { key: "provisioning", label: "Provisioning" },
                          { key: "connecting", label: "Connecting" },
                        ] as const;
                        const currentIndex = isProvisioningPhase ? 0 : 1;

                        return (
                          <>
                            <div className="flex items-center gap-3">
                              {phases.map((phase, idx) => {
                                const isCompleted = idx < currentIndex;
                                const isCurrent = idx === currentIndex;
                                return (
                                  <div key={phase.key} className="flex items-center">
                                    <div className="flex flex-col items-center">
                                      <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${isCompleted ? "bg-green-500/20 text-green-400" : isCurrent ? "bg-claude-accent/20 text-claude-accent ring-2 ring-claude-accent/30" : "bg-claude-bg-2 text-claude-text-muted"}`}>
                                        {isCompleted ? (
                                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                          </svg>
                                        ) : isCurrent ? (
                                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                          </svg>
                                        ) : (
                                          <span className="text-xs font-medium">{idx + 1}</span>
                                        )}
                                      </div>
                                      <span className={`mt-1.5 text-[10px] font-medium whitespace-nowrap ${isCurrent ? "text-claude-text-secondary" : "text-claude-text-muted"}`}>
                                        {phase.label}
                                      </span>
                                    </div>
                                    {idx < phases.length - 1 && (
                                      <div className={`w-12 h-0.5 mx-2 mb-5 transition-colors ${idx < currentIndex ? "bg-green-500/40" : "bg-claude-border"}`} />
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                            <div className="text-center">
                              <p className="font-medium text-claude-text-secondary mb-1">
                                {isProvisioningPhase ? "Setting up workspace" : "Connecting to agent"}
                              </p>
                              <p className="text-xs leading-relaxed text-claude-text-muted">
                                {isProvisioningPhase
                                  ? "Creating container and configuring the environment..."
                                  : "Waiting for the agent to establish connection."}
                              </p>
                              {status_message && (
                                <p className="mt-2 text-xs font-mono text-claude-text-secondary bg-claude-bg-2 rounded px-2 py-1">
                                  {status_message}
                                </p>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (
                    <>
                      <svg className="h-12 w-12 text-claude-accent/50 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <div className="text-center max-w-md">
                        <p className="font-medium text-claude-text-secondary mb-1">Preparing workspace</p>
                        <p className="text-xs leading-relaxed text-claude-text-muted">
                          The agent is connecting. Files will appear once ready.
                        </p>
                      </div>
                    </>
                  )}
                </>
              ) : (
                <>
                  <svg className="h-10 w-10 text-claude-text-muted/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>Select a file to view or edit</span>
                </>
              )}
            </div>
          )}
        </div>
        {terminalOpen && (
          <div className="flex-shrink-0 flex flex-col border-t border-claude-border" style={{ height: "280px" }}>
            <TerminalPanel agentId={agentId} token={token} onClose={() => setTerminalOpen(false)} />
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="Delete File"
        message={`Are you sure you want to delete "${deleteTarget?.split("/").pop()}"? This action cannot be undone.`}
        confirmLabel={deleteMut.isPending ? "Deleting…" : "Delete"}
        variant="danger"
      />

      {renameTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold text-claude-text-primary mb-4">Rename</h3>
            <input
              type="text"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") confirmRename(); if (e.key === "Escape") { setRenameTarget(null); setRenameValue(""); } }}
              className="w-full px-3 py-2 border border-claude-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-claude-accent/50"
              placeholder="New name"
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => { setRenameTarget(null); setRenameValue(""); }} className="px-3 py-1.5 text-sm text-claude-text-muted hover:text-claude-text-secondary">Cancel</button>
              <button type="button" onClick={confirmRename} disabled={!renameValue.trim() || renameMut.isPending} className="px-3 py-1.5 text-sm bg-claude-accent text-white rounded-lg hover:bg-claude-accent-hover disabled:opacity-50">
                {renameMut.isPending ? "Renaming…" : "Rename"}
              </button>
            </div>
          </div>
        </div>
      )}

      {moveTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-claude-text-primary mb-2">Move</h3>
            <p className="text-xs text-claude-text-muted mb-4">Enter the new path for "{moveTarget.split("/").pop()}"</p>
            <input
              type="text"
              value={moveDestValue}
              onChange={(e) => setMoveDestValue(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") confirmMove(); if (e.key === "Escape") { setMoveTarget(null); setMoveDestValue(""); } }}
              className="w-full px-3 py-2 border border-claude-border rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-claude-accent/50"
              placeholder="workspace/path/to/destination"
              autoFocus
            />
            <p className="text-[10px] text-claude-text-muted mt-2">Use paths relative to workspace root (e.g., workspace/folder/file.txt)</p>
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => { setMoveTarget(null); setMoveDestValue(""); }} className="px-3 py-1.5 text-sm text-claude-text-muted hover:text-claude-text-secondary">Cancel</button>
              <button type="button" onClick={confirmMove} disabled={!moveDestValue.trim() || moveMut.isPending} className="px-3 py-1.5 text-sm bg-claude-accent text-white rounded-lg hover:bg-claude-accent-hover disabled:opacity-50">
                {moveMut.isPending ? "Moving…" : "Move"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
