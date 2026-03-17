import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { Button, PageContainer } from "../components/ui";
import { useWorkspaceFiles, useWorkspaceFile, useSaveWorkspaceFile } from "../lib/queries";

export default function WorkspaceEditor() {
  const { agentId } = useParams();
  const { data: workspace } = useWorkspaceFiles(agentId);
  const files = workspace?.files ?? [];
  const [current, setCurrent] = useState("");
  const { data: fileContent } = useWorkspaceFile(agentId, current);
  const [content, setContent] = useState("");
  const dirtyRef = useRef(false);
  const saveMut = useSaveWorkspaceFile(agentId!);

  useEffect(() => {
    if (fileContent !== undefined && !dirtyRef.current) setContent(fileContent);
  }, [fileContent]);

  useEffect(() => {
    dirtyRef.current = false;
  }, [current]);

  return (
    <PageContainer wide className="flex h-[calc(100vh-8rem)] gap-3">
      <div className="w-48 overflow-y-auto rounded-xl border border-claude-border bg-claude-input p-2 text-sm">
        {files.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setCurrent(f)}
            className={`block w-full truncate rounded-lg px-2.5 py-1.5 text-left transition-colors ${current === f ? "bg-claude-surface-alt text-claude-text-primary font-medium" : "text-claude-text-tertiary hover:bg-claude-surface hover:text-claude-text-secondary"}`}
          >
            {f}
          </button>
        ))}
      </div>
      <div className="flex-1 rounded-xl border border-claude-border overflow-hidden">
        {current ? (
          <>
            <div className="flex justify-end border-b border-claude-border bg-claude-surface px-3 py-2">
              <Button
                size="sm"
                onClick={() => saveMut.mutate({ path: current, content }, { onSuccess: () => { dirtyRef.current = false; } })}
                disabled={saveMut.isPending}
              >
                {saveMut.isPending ? "Saving..." : "Save"}
              </Button>
            </div>
            <Editor
              height="100%"
              defaultLanguage="markdown"
              value={content}
              onChange={(v) => { dirtyRef.current = true; setContent(v ?? ""); }}
              theme="light"
              options={{ fontSize: 13, minimap: { enabled: false }, padding: { top: 12 } }}
            />
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-claude-text-muted text-sm">
            Select a file
          </div>
        )}
      </div>
    </PageContainer>
  );
}
