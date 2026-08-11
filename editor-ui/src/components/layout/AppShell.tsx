import { NavLink } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { resetCsrfToken } from "@/api/client";
import {
  FileText,
  Languages,
  Link2,
  LogOut,
  Network,
  Send,
  Settings,
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/features/auth/useAuth";
import { useT } from "@/i18n";
import type { MessageKey } from "@/i18n";

type NavItem = {
  to: string;
  labelKey: MessageKey;
  icon: typeof FileText;
  superuser?: boolean;
};

type NavGroup = {
  labelKey: MessageKey;
  items: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    labelKey: "nav.content",
    items: [{ to: "/posts", labelKey: "nav.posts", icon: FileText }],
  },
  {
    labelKey: "nav.publish",
    items: [{ to: "/publish", labelKey: "nav.multichannel", icon: Send }],
  },
  {
    labelKey: "nav.settings",
    items: [
      { to: "/config/networks", labelKey: "nav.networks", icon: Network },
      { to: "/config/telegram", labelKey: "nav.telegram", icon: Settings },
      {
        to: "/config/credentials",
        labelKey: "nav.credentials",
        icon: Shield,
        superuser: true,
      },
      { to: "/config/interface", labelKey: "nav.interface", icon: Languages },
    ],
  },
  {
    labelKey: "nav.audit",
    items: [{ to: "/audit/post-links", labelKey: "nav.postLinks", icon: Link2 }],
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  const t = useT();

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
          <span className="text-sm font-semibold tracking-tight">
            {t("nav.brand")}
          </span>
        </div>
        <nav className="min-h-0 flex-1 space-y-6 overflow-y-auto p-3">
          {navGroups.map((group) => (
            <div key={group.labelKey}>
              <div className="mb-2 px-2 text-xs font-semibold uppercase text-text-muted">
                {t(group.labelKey)}
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
                        {t(item.labelKey)}
                      </NavLink>
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="shrink-0 border-t border-border p-3">
          <div className="mb-2 truncate px-2 text-xs text-text-muted">
            {user?.email}
          </div>
          <button
            type="button"
            onClick={() => void handleLogout()}
            disabled={logout.isPending}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-text-secondary hover:bg-surface-muted disabled:opacity-60"
          >
            <LogOut className="h-4 w-4" />
            {t("nav.logout")}
          </button>
        </div>
      </aside>
      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </main>
    </div>
  );
}
