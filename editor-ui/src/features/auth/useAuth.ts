import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, fetchCsrf, resetCsrfToken } from "@/api/client";
import type { User } from "@/api/types";

interface MeResponse {
  ok: boolean;
  user: User;
}

interface LoginResponse {
  ok: boolean;
  step: "2fa" | "complete";
  user: User;
}

export function useAuth() {
  const queryClient = useQueryClient();
  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => apiFetch<MeResponse>("/auth/me/"),
    retry: false,
    refetchOnWindowFocus: false,
  });

  const loginMutation = useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      apiFetch<LoginResponse>("/auth/login/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: async (data) => {
      await fetchCsrf();
      queryClient.setQueryData(["auth", "me"], { ok: true, user: data.user });
    },
  });

  const verify2faMutation = useMutation({
    mutationFn: (token: string) =>
      apiFetch<MeResponse>("/auth/2fa/verify/", {
        method: "POST",
        body: JSON.stringify({ token }),
      }),
    onSuccess: async (data) => {
      await fetchCsrf();
      queryClient.setQueryData(["auth", "me"], data);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      await fetchCsrf();
      return apiFetch<{ ok: boolean }>("/auth/logout/", { method: "POST" });
    },
    onSuccess: () => {
      resetCsrfToken();
      loginMutation.reset();
      verify2faMutation.reset();
      queryClient.setQueryData(["auth", "me"], null);
      queryClient.removeQueries({ queryKey: ["auth", "me"] });
    },
  });

  const user =
    (meQuery.isSuccess ? meQuery.data?.user : null) ??
    loginMutation.data?.user ??
    null;
  const pending2fa =
    loginMutation.data?.step === "2fa" ||
    (Boolean(user?.has_2fa) && !user?.is_verified);

  return {
    user,
    pending2fa,
    loading: meQuery.isLoading,
    login: loginMutation,
    verify2fa: verify2faMutation,
    logout: logoutMutation,
    refetch: meQuery.refetch,
  };
}
