import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { Button, Card, PageContainer } from "../components/ui";
import { useAgentConfig, useSaveConfig } from "../lib/queries";

export default function ConfigEditor() {
  const { agentId } = useParams();
  const { data: configData } = useAgentConfig(agentId);
  const saveMut = useSaveConfig(agentId!);
  const [config, setConfig] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (configData) setConfig(JSON.stringify(configData, null, 2));
  }, [configData]);

  async function save() {
    if (!agentId) return;
    try {
      const parsed = JSON.parse(config);
      await saveMut.mutateAsync(parsed);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      alert("Invalid JSON: " + (e as Error).message);
    }
  }

  return (
    <PageContainer wide>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {agentId && (
            <Link to={`/agents/${agentId}`} className="text-sm text-claude-text-muted hover:text-claude-accent transition-colors">
              ← Agent
            </Link>
          )}
          <h1 className="text-lg font-semibold text-claude-text-primary">Config</h1>
        </div>
        <Button
          onClick={save}
          disabled={saveMut.isPending}
          variant={saved ? "secondary" : "primary"}
          className={saved ? "bg-green-50 text-green-700 ring-1 ring-green-200" : ""}
        >
          {saved ? "Saved ✓" : saveMut.isPending ? "Saving..." : "Save"}
        </Button>
      </div>
      <Card padding={false} className="overflow-hidden h-[70vh]">
        <Editor
          height="100%"
          language="json"
          value={config}
          onChange={(v) => setConfig(v ?? "")}
          theme="light"
          options={{ fontSize: 13, minimap: { enabled: false }, padding: { top: 12 } }}
        />
      </Card>
    </PageContainer>
  );
}
