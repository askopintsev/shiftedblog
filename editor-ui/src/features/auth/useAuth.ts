import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
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
  });

  const loginMutation = useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      apiFetch<LoginResponse>("/auth/login/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["auth", "me"], { ok: true, user: data.user });
    },
  });

  const verify2faMutation = useMutation({
    mutationFn: (token: string) =>
      apiFetch<MeResponse>("/auth/2fa/verify/", {
        method: "POST",
        body: JSON.stringify({ token }),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["auth", "me"], data);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ ok: boolean }>("/auth/logout/", { method: "POST" }),
    onSuccess: () => {
      queryClient.setQueryData(["auth", "me"], null);
    },
  });

  return {
    user: meQuery.data?.user ?? null,
    loading: meQuery.isLoading,
    login: loginMutation,
    verify2fa: verify2faMutation,
    logout: logoutMutation,
    refetch: meQuery.refetch,
  };
}
