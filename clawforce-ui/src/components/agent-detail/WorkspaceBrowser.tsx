import { useState, useCallback } from "react";
import { Button } from "../ui";
import Editor from "@monaco-editor/react";

interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
}

interface WorkspaceBrowserProps {
  fileTree: FileNode[];
  isLoading: boolean;
  selectedFile: string | null;
  fileContent: string | null;
  isFileLoading: boolean;
  isSaving: boolean;
  onSelectFile: (path: string) => void;
  onSaveFile: (params: { path: string; content: string }) => void;
  onDeleteFile: (path: string) => void;
  onRefresh: () => void;
}

/**
 * WorkspaceBrowser provides a file tree explorer with file editing capabilities.
 * Supports CRUD operations on the agent's workspace.
 */
export function WorkspaceBrowser({
  fileTree,
  isLoading,
  selectedFile,
  fileContent,
  isFileLoading,
  isSaving,
  onSelectFile,
  onSaveFile,
  onDeleteFile,
  onRefresh,
}: WorkspaceBrowserProps) {
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const [editingContent, setEditingContent] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  const toggleDir = useCallback((path: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const handleSelectFile = useCallback(
    (path: string, type: "file" | "directory") => {
      if (type === "directory") {
        toggleDir(path);
      } else {
        onSelectFile(path);
        setHasChanges(false);
        setEditingContent(null);
      }
    },
    [onSelectFile, toggleDir]
  );

  const handleEditorChange = useCallback((value: string | undefined) => {
    setEditingContent(value || "");
    setHasChanges(true);
  }, []);

  const handleSave = useCallback(() => {
    if (selectedFile && editingContent !== null) {
      onSaveFile({ path: selectedFile, content: editingContent });
      setHasChanges(false);
    }
  }, [selectedFile, editingContent, onSaveFile]);

  const renderFileTree = (nodes: FileNode[], depth = 0): React.ReactElement[] => {
    return nodes.map((node) => {
      const isExpanded = expandedDirs.has(node.path);
      const isSelected = selectedFile === node.path;
      const paddingLeft = depth * 16 + 12;

      return (
        <div key={node.path}>
          <div
            className={`flex items-center py-1.5 px-2 cursor-pointer hover:bg-claude-surface ${
              isSelected ? "bg-claude-surface" : ""
            }`}
            style={{ paddingLeft }}
            onClick={() => handleSelectFile(node.path, node.type)}
          >
            <span className="mr-2 text-claude-text-muted">
              {node.type === "directory" ? (isExpanded ? "📂" : "📁") : "📄"}
            </span>
            <span className="text-sm text-claude-text-primary truncate">{node.name}</span>
          </div>
          {node.type === "directory" && isExpanded && node.children && (
            <div>{renderFileTree(node.children, depth + 1)}</div>
          )}
        </div>
      );
    });
  };

  const getLanguage = (path: string): string => {
    const ext = path.split(".").pop()?.toLowerCase();
    const langMap: Record<string, string> = {
      js: "javascript",
      ts: "typescript",
      tsx: "typescript",
      jsx: "javascript",
      py: "python",
      json: "json",
      yaml: "yaml",
      yml: "yaml",
      md: "markdown",
      html: "html",
      css: "css",
      sh: "shell",
      bash: "shell",
    };
    return langMap[ext || ""] || "plaintext";
  };

  return (
    <div className="bg-claude-input rounded-xl border border-claude-border flex flex-col h-[600px]">
      <div className="px-4 py-3 border-b border-claude-border flex items-center justify-between">
        <h3 className="text-sm font-semibold text-claude-text-primary">Workspace</h3>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={onRefresh}>
            Refresh
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* File Tree Sidebar */}
        <div className="w-64 border-r border-claude-border overflow-y-auto">
          {isLoading ? (
            <div className="p-4 text-sm text-claude-text-secondary">Loading files...</div>
          ) : fileTree.length === 0 ? (
            <div className="p-4 text-sm text-claude-text-muted">No files in workspace</div>
          ) : (
            <div className="py-2">{renderFileTree(fileTree)}</div>
          )}
        </div>

        {/* Editor Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {selectedFile ? (
            <>
              <div className="px-4 py-2 border-b border-claude-border flex items-center justify-between bg-claude-surface">
                <span className="text-sm font-medium text-claude-text-primary">
                  {selectedFile}
                  {hasChanges && <span className="text-claude-accent ml-2">●</span>}
                </span>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={() => selectedFile && onDeleteFile(selectedFile)}>
                    Delete
                  </Button>
                  <Button size="sm" onClick={handleSave} disabled={!hasChanges || isSaving}>
                    {isSaving ? "Saving..." : "Save"}
                  </Button>
                </div>
              </div>
              <div className="flex-1 overflow-hidden">
                {isFileLoading ? (
                  <div className="flex items-center justify-center h-full text-claude-text-secondary">
                    Loading file...
                  </div>
                ) : (
                  <Editor
                    height="100%"
                    defaultLanguage={getLanguage(selectedFile)}
                    value={fileContent || ""}
                    onChange={handleEditorChange}
                    options={{
                      minimap: { enabled: false },
                      scrollBeyondLastLine: false,
                      fontSize: 14,
                      lineNumbers: "on",
                      roundedSelection: false,
                      padding: { top: 16 },
                    }}
                    theme="vs-dark"
                  />
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-claude-text-secondary">
              Select a file to view and edit
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
