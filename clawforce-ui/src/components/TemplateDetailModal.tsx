import { useState, useEffect } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import Modal from "./Modal";
import { ClawIcon } from "./ClawIcon";
import { useTemplateDetail } from "../lib/queries";

marked.setOptions({ breaks: true, gfm: true });

function renderMd(raw: string): string {
  return DOMPurify.sanitize(marked.parse(raw) as string);
}

function isMarkdown(path: string): boolean {
  return /\.(md|markdown)$/i.test(path);
}

interface TemplateDetailModalProps {
  open: boolean;
  templateId: string | null;
  onClose: () => void;
  onCreateClaw: (templateId: string) => void;
}

function FileItem({
  path,
  isActive,
  onClick,
}: {
  path: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-1.5 rounded py-[5px] pr-2 pl-2 text-left text-xs transition-colors ${
        isActive ? "bg-claude-accent/10 text-claude-accent font-medium" : "text-claude-text-secondary hover:bg-claude-surface-alt hover:text-claude-text-primary"
      }`}
    >
      <span className="truncate font-mono">{path}</span>
    </button>
  );
}

function ContentPane({ file }: { file: { path: string; content: string } | null }) {
  if (!file) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-claude-text-muted text-sm gap-2 p-8">
        <svg className="h-10 w-10 text-claude-text-muted/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <span>Select a file to view</span>
      </div>
    );
  }

  const asMd = isMarkdown(file.path);

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="mb-3 border-b border-claude-border pb-2">
        <span className="font-mono text-xs text-claude-text-muted">{file.path}</span>
      </div>
      {asMd ? (
        <div
          className="prose prose-sm max-w-none
            prose-headings:text-claude-text-primary prose-p:text-claude-text-secondary prose-li:text-claude-text-secondary
            prose-code:text-claude-text-primary prose-code:bg-claude-surface prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
            prose-pre:bg-claude-bg prose-pre:border prose-pre:border-claude-border prose-pre:rounded-lg"
          dangerouslySetInnerHTML={{ __html: renderMd(file.content) }}
        />
      ) : (
        <pre className="text-xs font-mono text-claude-text-secondary whitespace-pre-wrap break-words">
          {file.content}
        </pre>
      )}
    </div>
  );
}

export default function TemplateDetailModal({
  open,
  templateId,
  onClose,
  onCreateClaw,
}: TemplateDetailModalProps) {
  const { data: detail, isLoading, error } = useTemplateDetail(open && templateId ? templateId : undefined);
  const [currentPath, setCurrentPath] = useState<string>("");

  const allFiles = detail
    ? [...detail.profileFiles.map((f) => ({ ...f, section: "profile" as const })), ...detail.workspaceFiles.map((f) => ({ ...f, section: "workspace" as const }))]
    : [];
  const fileByPath = Object.fromEntries(allFiles.map((f) => [f.path, f]));
  const currentFile = currentPath ? fileByPath[currentPath] ?? null : null;

  useEffect(() => {
    if (detail) {
      const first = detail.profileFiles[0] ?? detail.workspaceFiles[0];
      setCurrentPath(first?.path ?? "");
    } else {
      setCurrentPath("");
    }
  }, [detail]);

  const footer = detail && (
    <>
      <button
        type="button"
        onClick={onClose}
        className="rounded-lg px-3 py-1.5 text-sm text-claude-text-muted hover:text-claude-text-secondary transition-colors"
      >
        Close
      </button>
      <button
        type="button"
        onClick={() => {
          onClose();
          onCreateClaw(detail.value);
        }}
        className="rounded-lg bg-claude-accent px-4 py-1.5 text-sm font-medium text-white hover:bg-claude-accent-hover transition-colors"
      >
        Create Claw →
      </button>
    </>
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={detail?.label ?? "Template Setup"}
      icon={<ClawIcon className="h-4 w-4" />}
      size="xl"
      footer={footer}
    >
      {isLoading && <p className="text-sm text-claude-text-muted">Loading setup...</p>}
      {error && (
        <p className="text-sm text-red-600">
          {error instanceof Error ? error.message : "Failed to load template"}
        </p>
      )}
      {detail && (
        <div className="flex h-[min(70vh,32rem)] gap-0 rounded-lg border border-claude-border overflow-hidden bg-white">
          {/* Explorer sidebar */}
          <div className="w-52 flex-shrink-0 border-r border-claude-border bg-claude-bg flex flex-col overflow-hidden">
            <div className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-claude-text-muted border-b border-claude-border">
              Files
            </div>
            <div className="flex-1 overflow-y-auto py-1">
              {detail.profileFiles.length > 0 && (
                <div className="mb-2">
                  <div className="flex items-center gap-1.5 px-2 py-1.5 text-[10px] font-medium text-claude-text-muted uppercase tracking-wider">
                    <span>📁</span> Profile
                  </div>
                  <div className="space-y-0.5">
                    {detail.profileFiles.map(({ path }) => (
                      <FileItem
                        key={path}
                        path={path}
                        isActive={currentPath === path}
                        onClick={() => setCurrentPath(path)}
                      />
                    ))}
                  </div>
                </div>
              )}
              {detail.workspaceFiles.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 px-2 py-1.5 text-[10px] font-medium text-claude-text-muted uppercase tracking-wider">
                    <span>📂</span> Workspace
                  </div>
                  <div className="space-y-0.5">
                    {detail.workspaceFiles.map(({ path }) => (
                      <FileItem
                        key={path}
                        path={path}
                        isActive={currentPath === path}
                        onClick={() => setCurrentPath(path)}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          {/* Content pane */}
          <div className="flex-1 flex flex-col overflow-hidden min-w-0">
            <ContentPane file={currentFile} />
          </div>
        </div>
      )}
    </Modal>
  );
}
