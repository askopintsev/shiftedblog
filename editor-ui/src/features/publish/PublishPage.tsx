import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import type { PostListItem, PublishResult, TelegramPreviewResponse } from "@/api/types";
import { useAuth } from "@/features/auth/useAuth";
import { PublishResultDialog } from "@/features/publish/PublishResultDialog";
import { TelegramPreviewCards } from "@/features/publish/TelegramPreviewCards";
import { useT } from "@/i18n";

export function PublishPage() {
  const { publicSiteEnabled } = useAuth();
  const [postId, setPostId] = useState<number | "">("");
  const [destSite, setDestSite] = useState(publicSiteEnabled);
  const [destTelegram, setDestTelegram] = useState(!publicSiteEnabled);
  const [telegramFormat, setTelegramFormat] = useState("full_text");
  const [crosslinkNetwork, setCrosslinkNetwork] = useState("");
  const [telegramStory, setTelegramStory] = useState(false);
  const [result, setResult] = useState<PublishResult | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const t = useT();

  useEffect(() => {
    if (!publicSiteEnabled) {
      setDestSite(false);
      setDestTelegram(true);
    }
  }, [publicSiteEnabled]);

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
    onMutate: () => {
      setResult(null);
      setRequestError(null);
    },
    onSuccess: (data) => setResult(data.result),
    onError: (error) => {
      setRequestError(
        t("publish.requestFailed", {
          message: error instanceof Error ? error.message : String(error),
        }),
      );
    },
  });

  return (
    <div className="p-6">
      {result && (
        <PublishResultDialog result={result} onClose={() => setResult(null)} />
      )}
      {requestError && !result && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setRequestError(null);
          }}
        >
          <div
            role="alertdialog"
            aria-modal="true"
            className="w-full max-w-md rounded-2xl border border-red-200 bg-surface p-5 shadow-xl"
          >
            <h2 className="text-lg font-semibold text-red-900">
              {t("publish.hasErrors")}
            </h2>
            <p className="mt-2 text-sm text-red-800">{requestError}</p>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => setRequestError(null)}
                className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
              >
                {t("common.close")}
              </button>
            </div>
          </div>
        </div>
      )}
      <h1 className="mb-6 text-2xl font-semibold">{t("publish.title")}</h1>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4 rounded-xl border border-border bg-surface p-4">
          <label className="block text-sm">
            {t("publish.postReady")}
            <select
              value={postId}
              onChange={(e) => {
                setPostId(e.target.value ? Number(e.target.value) : "");
                setShowPreview(false);
              }}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2"
            >
              <option value="">{t("publish.selectPost")}</option>
              {readyQuery.data?.results.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title || `#${p.id}`} ({p.slug})
                </option>
              ))}
            </select>
          </label>
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">{t("publish.channels")}</legend>
            {publicSiteEnabled && (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={destSite}
                  onChange={(e) => setDestSite(e.target.checked)}
                />
                {t("publish.site")}
              </label>
            )}
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={destTelegram}
                onChange={(e) => setDestTelegram(e.target.checked)}
              />
              {t("common.telegram")}
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
                {t("publish.fullPost")}
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="format"
                  checked={telegramFormat === "crosslink"}
                  onChange={() => setTelegramFormat("crosslink")}
                />
                {t("publish.crosslink")}
              </label>
              {telegramFormat === "crosslink" && (
                <select
                  value={crosslinkNetwork}
                  onChange={(e) => setCrosslinkNetwork(e.target.value)}
                  className="w-full rounded-lg border border-border px-2 py-1.5 text-sm"
                >
                  <option value="">{t("publish.crosslinkTarget")}</option>
                  {publicSiteEnabled && destSite && (
                    <option value="site">{t("publish.site")}</option>
                  )}
                </select>
              )}
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={telegramStory}
                  disabled={!storyQuery.data?.available}
                  onChange={(e) => setTelegramStory(e.target.checked)}
                />
                {t("publish.telegramStory")}
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
              {t("publish.previewButton")}
            </button>
            <button
              type="button"
              disabled={!postId || publishMutation.isPending}
              onClick={() => publishMutation.mutate()}
              className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
            >
              {t("publish.submit")}
            </button>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4">
          <h2 className="mb-3 font-medium">{t("publish.previewHeading")}</h2>
          {previewQuery.isFetching && (
            <p className="text-sm text-text-muted">{t("publish.previewLoading")}</p>
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
            <p className="text-sm text-text-muted">{t("publish.previewEmpty")}</p>
          ) : (
            <p className="text-sm text-text-muted">{t("publish.previewHint")}</p>
          )}
        </div>
      </div>
    </div>
  );
}
