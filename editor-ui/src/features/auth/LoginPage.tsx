import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./useAuth";

export function LoginPage() {
  const navigate = useNavigate();
  const { user, pending2fa, login, verify2fa } = useAuth();

  useEffect(() => {
    if (user?.is_staff && user.is_verified && !pending2fa) {
      navigate("/posts", { replace: true });
    }
  }, [user, pending2fa, navigate]);

  async function onLoginSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const result = await login.mutateAsync({
      email: String(fd.get("email") ?? ""),
      password: String(fd.get("password") ?? ""),
    });
    if (result.step === "complete" && result.user.is_verified) {
      navigate("/posts", { replace: true });
    }
  }

  async function on2faSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await verify2fa.mutateAsync(String(fd.get("token") ?? ""));
    navigate("/posts", { replace: true });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-muted p-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-surface p-8 shadow-sm">
        <div className="mb-6 text-center">
          <h1 className="text-xl font-semibold">Shifted Blog Editor</h1>
          <p className="mt-1 text-sm text-text-muted">Вход для редакторов</p>
        </div>
        {pending2fa ? (
          <form onSubmit={on2faSubmit} className="space-y-4">
            <p className="text-sm text-text-muted">
              Введите код из приложения аутентификации.
            </p>
            <label className="block text-sm font-medium">
              Код 2FA
              <input
                name="token"
                autoComplete="one-time-code"
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
                required
              />
            </label>
            {verify2fa.isError && (
              <p className="text-sm text-red-600">Неверный код.</p>
            )}
            <button
              type="submit"
              disabled={verify2fa.isPending}
              className="w-full rounded-lg bg-accent px-4 py-2 text-white disabled:opacity-60"
            >
              Подтвердить
            </button>
          </form>
        ) : (
          <form onSubmit={onLoginSubmit} className="space-y-4">
            <label className="block text-sm font-medium">
              Email
              <input
                name="email"
                type="email"
                autoComplete="username"
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
                required
              />
            </label>
            <label className="block text-sm font-medium">
              Пароль
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                className="mt-1 w-full rounded-lg border border-border px-3 py-2"
                required
              />
            </label>
            {login.isError && (
              <p className="text-sm text-red-600">Неверный email или пароль.</p>
            )}
            <button
              type="submit"
              disabled={login.isPending}
              className="w-full rounded-lg bg-accent px-4 py-2 text-white disabled:opacity-60"
            >
              Войти
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
