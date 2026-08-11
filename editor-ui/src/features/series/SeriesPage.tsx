import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import type { Series } from "@/api/types";
import { useT } from "@/i18n";

export function SeriesPage() {
  const queryClient = useQueryClient();
  const t = useT();
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["series"],
    queryFn: () =>
      apiFetch<{ ok: boolean; results: Series[] }>("/series/"),
  });

  const createMutation = useMutation({
    mutationFn: (name: string) =>
      apiFetch("/series/", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["series"] });
      setNewName("");
    },
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      apiFetch(`/series/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["series"] });
      setEditingId(null);
    },
  });

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold">{t("series.title")}</h1>
      <p className="mb-6 max-w-2xl text-sm text-text-muted">{t("series.help")}</p>

      <form
        className="mb-6 flex max-w-xl gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const name = newName.trim();
          if (!name) return;
          createMutation.mutate(name);
        }}
      >
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={t("series.namePlaceholder")}
          className="flex-1 rounded-lg border border-border px-2 py-1.5"
        />
        <button
          type="submit"
          disabled={createMutation.isPending || !newName.trim()}
          className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
        >
          {t("series.create")}
        </button>
      </form>

      {isLoading ? (
        <p className="text-text-muted">{t("common.loading")}</p>
      ) : (
        <ul className="max-w-xl space-y-2">
          {(data?.results ?? []).map((item) => (
            <li
              key={item.id}
              className="rounded-lg border border-border bg-surface px-4 py-3"
            >
              {editingId === item.id ? (
                <form
                  className="flex items-center gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    patchMutation.mutate({ id: item.id, name: editName.trim() });
                  }}
                >
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="flex-1 rounded-lg border border-border px-2 py-1"
                  />
                  <button type="submit" className="text-sm text-accent">
                    {t("common.save")}
                  </button>
                  <button
                    type="button"
                    className="text-sm text-text-muted"
                    onClick={() => setEditingId(null)}
                  >
                    {t("common.cancel")}
                  </button>
                </form>
              ) : (
                <div className="flex items-center justify-between">
                  <strong>{item.name}</strong>
                  <button
                    type="button"
                    className="text-sm text-accent"
                    onClick={() => {
                      setEditingId(item.id);
                      setEditName(item.name);
                    }}
                  >
                    {t("common.edit")}
                  </button>
                </div>
              )}
            </li>
          ))}
          {(data?.results ?? []).length === 0 ? (
            <li className="text-sm text-text-muted">{t("series.empty")}</li>
          ) : null}
        </ul>
      )}
    </div>
  );
}
