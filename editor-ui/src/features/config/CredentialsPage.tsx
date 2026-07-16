import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useAuth } from "@/features/auth/useAuth";

interface CredentialRow {
  id: number;
  network: number;
  network_slug: string;
  label: string;
}

interface CredentialDetail extends CredentialRow {
  secrets_masked: Record<string, unknown>;
}

export function CredentialsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [secretsJson, setSecretsJson] = useState("{}");
  const [label, setLabel] = useState("");

  const { data } = useQuery({
    queryKey: ["credentials"],
    enabled: Boolean(user?.is_superuser),
    queryFn: () =>
      apiFetch<{ ok: boolean; results: CredentialRow[] }>("/config/credentials/"),
  });

  const detailQuery = useQuery({
    queryKey: ["credential", editingId],
    enabled: editingId !== null,
    queryFn: () =>
      apiFetch<{ ok: boolean; credential: CredentialDetail }>(
        `/config/credentials/${editingId}/`,
      ),
  });

  const patchMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: { label?: string; secrets?: Record<string, unknown> };
    }) =>
      apiFetch(`/config/credentials/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["credentials"] });
      setEditingId(null);
    },
  });

  if (!user?.is_superuser) {
    return (
      <div className="p-6">
        <h1 className="mb-4 text-2xl font-semibold">Credentials</h1>
        <p className="text-sm text-text-muted">Доступ только для superuser.</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold">Credentials</h1>
      <ul className="space-y-2">
        {data?.results.map((c) => (
          <li key={c.id} className="rounded-lg border border-border bg-surface px-4 py-3">
            <div className="flex items-center justify-between">
              <span>
                {c.network_slug}:{c.label || "default"}
              </span>
              <button
                type="button"
                className="text-sm text-accent"
                onClick={() => {
                  setEditingId(c.id);
                  setLabel(c.label);
                }}
              >
                Редактировать
              </button>
            </div>
          </li>
        ))}
      </ul>
      {editingId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <form
            className="w-full max-w-lg rounded-xl border border-border bg-surface p-4"
            onSubmit={(e) => {
              e.preventDefault();
              let secrets: Record<string, unknown> | undefined;
              try {
                secrets = JSON.parse(secretsJson) as Record<string, unknown>;
              } catch {
                window.alert("Некорректный JSON secrets");
                return;
              }
              patchMutation.mutate({
                id: editingId,
                payload: { label, secrets },
              });
            }}
          >
            <h2 className="mb-3 font-semibold">Редактирование credential</h2>
            <label className="mb-3 block text-sm">
              Label
              <input
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              />
            </label>
            <p className="mb-1 text-xs text-text-muted">
              Текущие ключи (masked):{" "}
              {JSON.stringify(detailQuery.data?.credential.secrets_masked ?? {})}
            </p>
            <label className="mb-3 block text-sm">
              Secrets (JSON)
              <textarea
                value={secretsJson}
                onChange={(e) => setSecretsJson(e.target.value)}
                rows={8}
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5 font-mono text-xs"
              />
            </label>
            <div className="flex gap-2">
              <button
                type="submit"
                className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
              >
                Сохранить
              </button>
              <button
                type="button"
                className="rounded-lg border border-border px-4 py-2 text-sm"
                onClick={() => setEditingId(null)}
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
