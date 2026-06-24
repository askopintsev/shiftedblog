import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

export function TelegramSettingsPage() {
  const queryClient = useQueryClient();
  const [continuationText, setContinuationText] = useState("");

  const { data } = useQuery({
    queryKey: ["telegram-settings"],
    queryFn: () =>
      apiFetch<{
        ok: boolean;
        settings: { post_continuation_text: string | null } | null;
      }>("/config/telegram-settings/"),
  });

  useEffect(() => {
    if (data?.settings) {
      setContinuationText(data.settings.post_continuation_text ?? "");
    }
  }, [data?.settings]);

  const patchMutation = useMutation({
    mutationFn: () =>
      apiFetch("/config/telegram-settings/", {
        method: "PATCH",
        body: JSON.stringify({ post_continuation_text: continuationText || null }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["telegram-settings"] });
    },
  });

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold">Telegram settings</h1>
      {data?.settings ? (
        <form
          className="max-w-xl space-y-4 rounded-lg border border-border bg-surface p-4"
          onSubmit={(e) => {
            e.preventDefault();
            patchMutation.mutate();
          }}
        >
          <label className="block text-sm">
            Текст продолжения поста
            <textarea
              value={continuationText}
              onChange={(e) => setContinuationText(e.target.value)}
              rows={4}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <button
            type="submit"
            disabled={patchMutation.isPending}
            className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
          >
            Сохранить
          </button>
        </form>
      ) : (
        <p className="text-text-muted">Не настроено.</p>
      )}
    </div>
  );
}
