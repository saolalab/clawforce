import { useState, useRef, useEffect } from "react";
import { Outlet, NavLink, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { ClawIcon } from "./ClawIcon";
import { PlanIcon, MarketplaceIcon } from "./ui";
import clawforceLogo from "../assets/clawforce.png";

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (popRef.current && !popRef.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center justify-center rounded-lg px-3 py-2 transition-colors ${
      isActive
        ? "bg-claude-sidebar-active text-claude-text-primary font-medium"
        : "text-claude-text-tertiary hover:bg-claude-sidebar-hover hover:text-claude-text-secondary"
    }`;

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-14 flex-col border-r border-claude-border bg-claude-sidebar py-3 text-sm">
        <div className="mb-4 flex items-center justify-center">
          <img src={clawforceLogo} alt="Clawforce" className="w-11 h-11 shrink-0 rounded-lg" />
        </div>

        <nav className="space-y-0.5 px-1.5">
          <NavLink to="/claws" className={linkClass} title="Claws">
            <ClawIcon className="h-5 w-5 shrink-0" />
          </NavLink>
          <NavLink to="/plans" className={linkClass} title="Plans">
            <PlanIcon className="h-5 w-5 shrink-0" />
          </NavLink>
          <NavLink to="/marketplace" className={linkClass} title="Marketplace">
            <MarketplaceIcon className="h-5 w-5 shrink-0" />
          </NavLink>
        </nav>

        <div ref={popRef} className="relative mt-auto pt-2 px-1.5">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex w-full items-center justify-center rounded-lg px-2 py-1.5 text-claude-text-secondary hover:bg-claude-sidebar-hover transition-colors"
            title={user?.username}
          >
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-claude-accent/20 text-xs font-medium text-claude-accent">
              {user?.username?.charAt(0).toUpperCase()}
            </div>
          </button>
          {open && (
            <div className="absolute bottom-0 left-full ml-1 w-48 rounded-lg border border-claude-border bg-claude-sidebar shadow-lg py-1">
              {/* Profile */}
              <div className="border-b border-claude-border px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-claude-accent/20 text-sm font-medium text-claude-accent">
                    {user?.username?.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-xs font-medium text-claude-text-primary">{user?.username}</p>
                    <p className="truncate text-[10px] text-claude-text-tertiary">{user?.role ?? "—"}</p>
                  </div>
                </div>
              </div>
              <Link
                to="/admin/settings"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 px-3 py-2 text-xs text-claude-text-tertiary hover:bg-claude-sidebar-hover hover:text-claude-text-primary transition-colors"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Settings
              </Link>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  logout();
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-xs text-claude-text-tertiary hover:bg-claude-sidebar-hover hover:text-claude-text-primary transition-colors"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Logout
              </button>
            </div>
          )}
        </div>
      </aside>
      <main className="ml-14 flex-1 overflow-auto p-6 bg-claude-bg min-h-screen">
        <Outlet />
      </main>
    </div>
  );
}
