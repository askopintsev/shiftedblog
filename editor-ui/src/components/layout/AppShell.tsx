import { NavLink, useNavigate } from "react-router-dom";
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
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
        <div className="border-b border-border px-4 py-5">
          <span className="text-sm font-semibold tracking-tight">Shifted Editor</span>
        </div>
        <nav className="flex-1 space-y-6 p-3">
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
        <div className="border-t border-border p-3">
          <div className="mb-2 truncate px-2 text-xs text-text-muted">{user?.email}</div>
          <button
            type="button"
            onClick={async () => {
              await logout.mutateAsync();
              navigate("/login");
            }}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-text-secondary hover:bg-surface-muted"
          >
            <LogOut className="h-4 w-4" />
            Выйти
          </button>
        </div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex-1 overflow-auto">{children}</div>
      </main>
    </div>
  );
}
