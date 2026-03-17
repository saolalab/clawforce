import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { getApiBase } from "../lib/api";

type User = { id: string; username: string; role: string } | null;

const AuthContext = createContext<{
  user: User;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
} | null>(null);

function apiBase(): string {
  return `${getApiBase()}/api`;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  const login = useCallback(async (username: string, password: string) => {
    const form = new FormData();
    form.set("username", username);
    form.set("password", password);
    const r = await fetch(`${apiBase()}/auth/login`, { method: "POST", body: form });
    if (!r.ok) throw new Error("Invalid credentials");
    const data = await r.json();
    setToken(data.access_token);
    localStorage.setItem("token", data.access_token);
    const me = await fetch(`${apiBase()}/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });
    const u = await me.json();
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("token");
  }, []);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    fetch(`${apiBase()}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setUser)
      .catch(logout)
      .finally(() => setLoading(false));
  }, [token, logout]);

  useEffect(() => {
    const onExpired = () => logout();
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, [logout]);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
