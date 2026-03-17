import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import ClawsList from "./pages/ClawsList";
import PlansList from "./pages/PlansList";
import PlanBoard from "./pages/PlanBoard";
import AgentDetail from "./pages/AgentDetail";
import WorkspaceEditor from "./pages/WorkspaceEditor";
import LiveLogs from "./pages/LiveLogs";
import ConfigEditor from "./pages/ConfigEditor";
import AdminSettings from "./pages/AdminSettings";
import Marketplace from "./pages/Marketplace";

function Protected({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) return <div className="p-4">Loading...</div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Navigate to="/claws" replace />} />
        <Route path="claws" element={<ClawsList />} />
        <Route path="plans" element={<PlansList />} />
        <Route path="plans/:planId" element={<PlanBoard />} />
        <Route path="agents/:agentId" element={<AgentDetail />} />
        <Route path="agents/:agentId/workspace" element={<WorkspaceEditor />} />
        <Route path="agents/:agentId/logs" element={<LiveLogs />} />
        <Route path="agents/:agentId/config" element={<ConfigEditor />} />
        <Route path="marketplace" element={<Marketplace />} />
        <Route path="admin/settings" element={<AdminSettings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
