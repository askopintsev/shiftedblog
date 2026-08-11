import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { LoadingFallback } from "@/components/LoadingFallback";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/features/auth/useAuth";
import { LoginPage } from "@/features/auth/LoginPage";
import { PostLinksPage } from "@/features/audit/PostLinksPage";
import { CredentialsPage } from "@/features/config/CredentialsPage";
import { InterfacePage } from "@/features/config/InterfacePage";
import { NetworksPage } from "@/features/config/NetworksPage";
import { SiteSettingsPage } from "@/features/config/SiteSettingsPage";
import { TelegramSettingsPage } from "@/features/config/TelegramSettingsPage";
import { PostsListPage } from "@/features/posts/PostsListPage";
import { PublishPage } from "@/features/publish/PublishPage";
import { SessionKeepalive } from "@/features/auth/SessionKeepalive";
import { useT } from "@/i18n";

const PostEditPage = lazy(() =>
  import("@/features/posts/PostEditPage").then((module) => ({
    default: module.PostEditPage,
  })),
);

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading, pending2fa } = useAuth();
  const t = useT();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-text-muted">
        {t("common.loading")}
      </div>
    );
  }
  if (!user?.is_staff || pending2fa) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <>
      <SessionKeepalive />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppShell>
                <Suspense
                  fallback={
                    <LoadingFallback className="min-h-[50vh] p-6" />
                  }
                >
                  <Routes>
                    <Route path="/" element={<Navigate to="/posts" replace />} />
                    <Route path="/posts" element={<PostsListPage />} />
                    <Route path="/posts/new" element={<PostEditPage />} />
                    <Route path="/posts/:id" element={<PostEditPage />} />
                    <Route path="/publish" element={<PublishPage />} />
                    <Route path="/config/site" element={<SiteSettingsPage />} />
                    <Route path="/config/networks" element={<NetworksPage />} />
                    <Route
                      path="/config/credentials"
                      element={<CredentialsPage />}
                    />
                    <Route
                      path="/config/telegram"
                      element={<TelegramSettingsPage />}
                    />
                    <Route
                      path="/config/interface"
                      element={<InterfacePage />}
                    />
                    <Route path="/audit/post-links" element={<PostLinksPage />} />
                  </Routes>
                </Suspense>
              </AppShell>
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  );
}
