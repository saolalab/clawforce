import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Button, Input } from "../components/ui";
import clawforceLogo from "../assets/clawforce.png";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch {
      setError("Invalid username or password");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-claude-bg">
      <form onSubmit={handleSubmit} className="w-80 rounded-xl border border-claude-border bg-claude-input p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-center gap-2">
          <img src={clawforceLogo} alt="Clawforce" className="h-16 w-16 shrink-0" />
          <span className="text-lg font-semibold text-claude-text-primary">ClawForce</span>
        </div>
        {error && <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
        <Input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          className="mb-3 w-full"
        />
        <Input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          className="mb-5 w-full"
        />
        <Button type="submit" className="w-full">
          Log in
        </Button>
      </form>
    </div>
  );
}
