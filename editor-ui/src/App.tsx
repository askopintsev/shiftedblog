import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/features/auth/useAuth";
import { LoginPage } from "@/features/auth/LoginPage";
import { PostLinksPage } from "@/features/audit/PostLinksPage";
import { CredentialsPage } from "@/features/config/CredentialsPage";
import { NetworksPage } from "@/features/config/NetworksPage";
import { TelegramSettingsPage } from "@/features/config/TelegramSettingsPage";
import { PostEditPage } from "@/features/posts/PostEditPage";
import { PostsListPage } from "@/features/posts/PostsListPage";
import { PublishPage } from "@/features/publish/PublishPage";
import { SessionKeepalive } from "@/features/auth/SessionKeepalive";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-text-muted">
        Загрузка…
      </div>
    );
  }
  if (!user?.is_staff || (user.has_2fa && !user.is_verified)) {
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
                <Routes>
                  <Route path="/" element={<Navigate to="/posts" replace />} />
                  <Route path="/posts" element={<PostsListPage />} />
                  <Route path="/posts/new" element={<PostEditPage />} />
                  <Route path="/posts/:id" element={<PostEditPage />} />
                  <Route path="/publish" element={<PublishPage />} />
                  <Route path="/config/networks" element={<NetworksPage />} />
                  <Route path="/config/credentials" element={<CredentialsPage />} />
                  <Route path="/config/telegram" element={<TelegramSettingsPage />} />
                  <Route path="/audit/post-links" element={<PostLinksPage />} />
                </Routes>
              </AppShell>
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  );
}
