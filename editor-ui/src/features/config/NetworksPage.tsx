import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

export function NetworksPage() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

  const { data } = useQuery({
    queryKey: ["networks"],
    queryFn: () =>
      apiFetch<{ ok: boolean; results: { id: number; slug: string; name: string }[] }>(
        "/config/networks/",
      ),
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      apiFetch(`/config/networks/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["networks"] });
      setEditingId(null);
    },
  });

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold">Сети</h1>
      <ul className="space-y-2">
        {data?.results.map((n) => (
          <li key={n.id} className="rounded-lg border border-border bg-surface px-4 py-3">
            {editingId === n.id ? (
              <form
                className="flex items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  patchMutation.mutate({ id: n.id, name: editName });
                }}
              >
                <input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="flex-1 rounded-lg border border-border px-2 py-1"
                />
                <button type="submit" className="text-accent text-sm">
                  Сохранить
                </button>
                <button
                  type="button"
                  className="text-sm text-text-muted"
                  onClick={() => setEditingId(null)}
                >
                  Отмена
                </button>
              </form>
            ) : (
              <div className="flex items-center justify-between">
                <div>
                  <strong>{n.name}</strong>
                  <span className="ml-2 text-sm text-text-muted">{n.slug}</span>
                </div>
                <button
                  type="button"
                  className="text-sm text-accent"
                  onClick={() => {
                    setEditingId(n.id);
                    setEditName(n.name);
                  }}
                >
                  Изменить
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
