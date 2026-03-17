import { api } from "../../../lib/api";
import { triggerDownload } from "../utils";
import { ChevronIcon, FileIcon, FolderIcon } from "../ui/Icons";
import type { TreeNode } from "../types";

export function TreeItem({
  node,
  depth,
  current,
  onSelect,
  expanded,
  toggleExpand,
  agentId,
  onDelete,
  onRename,
  onMove,
}: {
  node: TreeNode;
  depth: number;
  current: string;
  onSelect: (path: string) => void;
  expanded: Set<string>;
  toggleExpand: (path: string) => void;
  agentId?: string;
  onDelete?: (path: string) => void;
  onRename?: (path: string) => void;
  onMove?: (path: string) => void;
}) {
  const isDir = node.isDir;
  const isOpen = expanded.has(node.path);
  const isActive = current === node.path;
  const isRootFolder = depth === 0 && isDir;
  const hasChildren = node.children.length > 0;
  const isWorkspace = node.path.startsWith("workspace/") || node.path === "workspace";
  const canModify = isWorkspace && !isRootFolder;

  return (
    <>
      <div className="group flex items-center">
        <button
          type="button"
          onClick={() => (isDir ? toggleExpand(node.path) : onSelect(node.path))}
          className={`flex flex-1 min-w-0 items-center gap-1 rounded py-[3px] pr-1 text-left transition-colors ${isActive
              ? "bg-claude-accent/10 text-claude-accent"
              : "text-claude-text-secondary hover:bg-claude-surface-alt"
            }`}
          style={{ paddingLeft: `${depth * 12 + 4}px` }}
        >
          {isDir ? <ChevronIcon open={isOpen} /> : <span className="w-3" />}
          {isDir ? <FolderIcon open={isOpen} /> : <FileIcon name={node.name} />}
          <span className={`truncate font-mono text-xs ${isActive ? "font-medium" : ""}`}>{node.name}</span>
          {isRootFolder && !hasChildren && (
            <span className="ml-auto text-[10px] text-claude-text-muted/60 italic">empty</span>
          )}
        </button>
        <div className="shrink-0 flex items-center gap-0.5 mr-1 opacity-0 group-hover:opacity-100 transition-all">
          {canModify && onRename && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onRename(node.path); }}
              className="p-0.5 rounded text-claude-text-muted hover:text-claude-text-secondary hover:bg-claude-surface-alt"
              title="Rename"
            >
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
          )}
          {canModify && onMove && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onMove(node.path); }}
              className="p-0.5 rounded text-claude-text-muted hover:text-claude-text-secondary hover:bg-claude-surface-alt"
              title="Move"
            >
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </button>
          )}
          {canModify && onDelete && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onDelete(node.path); }}
              className="p-0.5 rounded text-claude-text-muted hover:text-red-500 hover:bg-red-50"
              title="Delete"
            >
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
          {isDir && hasChildren && agentId && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                triggerDownload(
                  api.agents.downloadFolderZipUrl(agentId, node.path),
                  `${node.name}.zip`,
                );
              }}
              className="p-0.5 rounded text-claude-text-muted hover:text-claude-text-secondary hover:bg-claude-surface-alt"
              title={`Download ${node.name} as zip`}
            >
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </button>
          )}
        </div>
      </div>
      {isDir && isOpen && node.children.map((child) => (
        <TreeItem
          key={child.path}
          node={child}
          depth={depth + 1}
          current={current}
          onSelect={onSelect}
          expanded={expanded}
          toggleExpand={toggleExpand}
          agentId={agentId}
          onDelete={onDelete}
          onRename={onRename}
          onMove={onMove}
        />
      ))}
    </>
  );
}
