import { NavLink } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { resetCsrfToken } from "@/api/client";
import {
  FileText,
  Link2,
  LogOut,
  Network,
  Send,
  Settings,
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/features/auth/useAuth";

const navGroups = [
  {
    label: "Контент",
    items: [{ to: "/posts", label: "Посты", icon: FileText }],
  },
  {
    label: "Публикация",
    items: [{ to: "/publish", label: "Мультиканал", icon: Send }],
  },
  {
    label: "Настройки",
    items: [
      { to: "/config/networks", label: "Сети", icon: Network },
      { to: "/config/telegram", label: "Telegram", icon: Settings },
      { to: "/config/credentials", label: "Credentials", icon: Shield, superuser: true },
    ],
  },
  {
    label: "Аудит",
    items: [{ to: "/audit/post-links", label: "Post links", icon: Link2 }],
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();

  async function handleLogout() {
    try {
      await logout.mutateAsync();
    } catch {
      resetCsrfToken();
      queryClient.setQueryData(["auth", "me"], null);
      queryClient.removeQueries({ queryKey: ["auth", "me"] });
    } finally {
      window.location.assign("/login");
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-border bg-surface">
        <div className="shrink-0 border-b border-border px-4 py-5">
          <span className="text-sm font-semibold tracking-tight">Shifted Editor</span>
        </div>
        <nav className="min-h-0 flex-1 space-y-6 overflow-y-auto p-3">
          {navGroups.map((group) => (
            <div key={group.label}>
              <div className="mb-2 px-2 text-xs font-semibold uppercase text-text-muted">
                {group.label}
              </div>
              <ul className="space-y-1">
                {group.items
                  .filter((item) => !item.superuser || user?.is_superuser)
                  .map((item) => (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        className={({ isActive }) =>
                          cn(
                            "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition",
                            isActive
                              ? "border-l-2 border-accent bg-surface-muted font-medium"
                              : "text-text-secondary hover:bg-surface-muted",
                          )
                        }
                      >
                        <item.icon className="h-4 w-4" />
                        {item.label}
                      </NavLink>
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="shrink-0 border-t border-border p-3">
          <div className="mb-2 truncate px-2 text-xs text-text-muted">{user?.email}</div>
          <button
            type="button"
            onClick={() => void handleLogout()}
            disabled={logout.isPending}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-text-secondary hover:bg-surface-muted disabled:opacity-60"
          >
            <LogOut className="h-4 w-4" />
            Выйти
          </button>
        </div>
      </aside>
      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </main>
    </div>
  );
}
