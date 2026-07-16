import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import type { PostListItem, PublishResult, TelegramPreviewResponse } from "@/api/types";
import { TelegramPreviewCards } from "@/features/publish/TelegramPreviewCards";

export function PublishPage() {
  const [postId, setPostId] = useState<number | "">("");
  const [destSite, setDestSite] = useState(true);
  const [destTelegram, setDestTelegram] = useState(false);
  const [telegramFormat, setTelegramFormat] = useState("full_text");
  const [crosslinkNetwork, setCrosslinkNetwork] = useState("");
  const [telegramStory, setTelegramStory] = useState(false);
  const [result, setResult] = useState<PublishResult | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const readyQuery = useQuery({
    queryKey: ["publish-ready"],
    queryFn: () =>
      apiFetch<{ ok: boolean; results: PostListItem[] }>("/publish/ready/"),
  });

  const storyQuery = useQuery({
    queryKey: ["story-availability"],
    queryFn: () =>
      apiFetch<{ ok: boolean; available: boolean; reason: string }>(
        "/publish/story-availability/",
      ),
  });

  const previewQuery = useQuery({
    queryKey: ["telegram-preview", postId, telegramFormat, crosslinkNetwork],
    enabled: Boolean(postId) && showPreview,
    queryFn: () => {
      const params = new URLSearchParams({
        post_id: String(postId),
        telegram_format: telegramFormat,
      });
      if (crosslinkNetwork) params.set("crosslink_network", crosslinkNetwork);
      return apiFetch<TelegramPreviewResponse>(
        `/publish/telegram-preview/?${params}`,
      );
    },
  });

  const publishMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ ok: boolean; result: PublishResult }>("/publish/", {
        method: "POST",
        body: JSON.stringify({
          post_id: postId,
          dest_site: destSite,
          dest_telegram: destTelegram,
          telegram_format: telegramFormat,
          crosslink_network: crosslinkNetwork || null,
          telegram_post_story: telegramStory,
        }),
      }),
    onSuccess: (data) => setResult(data.result),
  });

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-semibold">Мультиканальная публикация</h1>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4 rounded-xl border border-border bg-surface p-4">
          <label className="block text-sm">
            Пост (готов к публикации)
            <select
              value={postId}
              onChange={(e) => {
                setPostId(e.target.value ? Number(e.target.value) : "");
                setShowPreview(false);
              }}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            >
              <option value="">— выберите —</option>
              {readyQuery.data?.results.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title || `#${p.id}`} ({p.slug})
                </option>
              ))}
            </select>
          </label>
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Каналы</legend>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={destSite}
                onChange={(e) => setDestSite(e.target.checked)}
              />
              Сайт (SitePublication)
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={destTelegram}
                onChange={(e) => setDestTelegram(e.target.checked)}
              />
              Telegram
            </label>
          </fieldset>
          {destTelegram && (
            <div className="space-y-2 border-l-2 border-border pl-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="format"
                  checked={telegramFormat === "full_text"}
                  onChange={() => setTelegramFormat("full_text")}
                />
                Полный пост
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="format"
                  checked={telegramFormat === "crosslink"}
                  onChange={() => setTelegramFormat("crosslink")}
                />
                Crosslink
              </label>
              {telegramFormat === "crosslink" && (
                <select
                  value={crosslinkNetwork}
                  onChange={(e) => setCrosslinkNetwork(e.target.value)}
                  className="w-full rounded-lg border border-border px-2 py-1.5 text-sm"
                >
                  <option value="">— цель crosslink —</option>
                  {destSite && <option value="site">Site</option>}
                </select>
              )}
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={telegramStory}
                  disabled={!storyQuery.data?.available}
                  onChange={(e) => setTelegramStory(e.target.checked)}
                />
                Telegram Story
              </label>
              {storyQuery.data && (
                <p className="text-xs text-text-muted">{storyQuery.data.reason}</p>
              )}
            </div>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!postId}
              onClick={() => setShowPreview(true)}
              className="rounded-lg border border-border px-4 py-2 text-sm"
            >
              Превью Telegram
            </button>
            <button
              type="button"
              disabled={!postId || publishMutation.isPending}
              onClick={() => publishMutation.mutate()}
              className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
            >
              Опубликовать
            </button>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4">
          <h2 className="mb-3 font-medium">Превью Telegram</h2>
          {previewQuery.isFetching && (
            <p className="text-sm text-text-muted">Загрузка превью…</p>
          )}
          {previewQuery.data?.preview_cards?.length ? (
            <TelegramPreviewCards
              cards={previewQuery.data.preview_cards}
              previewPayload={previewQuery.data.preview_payload}
              layoutSource={previewQuery.data.telegram_layout_source}
              ownerPremium={previewQuery.data.telegram_owner_premium}
              telegramFormat={telegramFormat}
            />
          ) : showPreview && !previewQuery.isFetching ? (
            <p className="text-sm text-text-muted">Нет данных превью для выбранного поста.</p>
          ) : (
            <p className="text-sm text-text-muted">
              Выберите пост и нажмите «Превью Telegram».
            </p>
          )}
          {result && (
            <div className="mt-4 border-t border-border pt-4">
              <h3 className="font-medium">
                {result.all_ok ? "Успешно" : "Есть ошибки"}
              </h3>
              <ul className="mt-2 space-y-1 text-sm">
                {Object.entries(result.by_network).map(([network, item]) => (
                  <li key={network}>
                    <strong>{network}:</strong>{" "}
                    {item.ok ? (
                      item.message_url ? (
                        <a href={item.message_url} target="_blank" rel="noreferrer">
                          {item.message_url}
                        </a>
                      ) : (
                        "OK"
                      )
                    ) : (
                      <span className="text-red-600">{item.error || item.detail}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
