import type { TelegramPreviewCard, TelegramPreviewPayload } from "@/api/types";
import {
  translateCardTitle,
  translateLayoutSource,
  translateLimitNote,
  translateStepLabel,
} from "@/features/publish/previewI18n";
import { useT } from "@/i18n";

interface TelegramPreviewCardsProps {
  cards: TelegramPreviewCard[];
  previewPayload?: TelegramPreviewPayload | null;
  layoutSource?: string | null;
  ownerPremium?: boolean | null;
  telegramFormat?: string;
}

export function TelegramPreviewCards({
  cards,
  previewPayload,
  layoutSource,
  ownerPremium,
  telegramFormat,
}: TelegramPreviewCardsProps) {
  const t = useT();
  const layoutText = translateLayoutSource(layoutSource);

  return (
    <div className="space-y-4">
      {layoutText && (
        <p className="text-xs text-text-muted">
          {layoutText}
          {ownerPremium !== null && ownerPremium !== undefined && (
            <>
              {" "}
              {t("preview.ownerPremium", {
                value: ownerPremium ? t("preview.yes") : t("preview.no"),
              })}
              .
            </>
          )}
        </p>
      )}
      {previewPayload && (
        <p className="text-xs text-text-muted">
          {previewPayload.is_series
            ? t("preview.series", { n: previewPayload.step_count })
            : t("preview.singlePost")}
          {t("preview.sendsTotal", { n: previewPayload.send_count })}
          {previewPayload.has_subscription
            ? t("preview.premiumChannel")
            : previewPayload.uses_rich_messages
              ? t("preview.richMessage")
              : telegramFormat === "crosslink"
                ? t("preview.crosslink")
                : t("preview.standardLayout")}
        </p>
      )}
      <div className="space-y-4">
        {cards.map((card, idx) => (
          <article
            key={`${card.send_index}-${idx}`}
            className="overflow-hidden rounded-xl border border-border bg-surface"
          >
            <header className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-muted px-3 py-2 text-xs">
              <span className="rounded bg-accent/10 px-2 py-0.5 font-medium text-accent">
                {t("preview.send", {
                  i: card.send_index,
                  total: card.send_total,
                })}
              </span>
              <strong className="text-sm text-text-primary">
                {translateCardTitle(card.title)}
              </strong>
              <span className="text-text-muted">
                {t("preview.step", {
                  i: card.step_index,
                  total: card.step_total,
                })}{" "}
                — {translateStepLabel(card.step_label)}
                {card.step_is_continuation ? t("preview.continuation") : ""}
              </span>
              {card.max_chars ? (
                <span
                  className={
                    card.char_count > card.max_chars
                      ? "font-medium text-red-600"
                      : "text-text-muted"
                  }
                >
                  {t("preview.chars", {
                    n: card.char_count,
                    m: card.max_chars,
                  })}
                </span>
              ) : card.kind === "media_group" ? (
                <span className="text-text-muted">
                  {t("preview.photos", { n: card.image_count ?? 0 })}
                </span>
              ) : null}
            </header>
            <div className="space-y-3 p-3">
              {card.limit_note && (
                <p className="text-xs text-amber-700">
                  {translateLimitNote(card.limit_note, card)}
                </p>
              )}
              {card.kind !== "rich_message" && card.cover_url && (
                <img
                  src={card.cover_url}
                  alt={t("preview.coverAlt")}
                  className="max-h-48 rounded-lg object-cover"
                />
              )}
              {card.kind !== "rich_message" &&
              card.thumb_row &&
              card.thumb_urls?.length ? (
                <div className="flex flex-wrap gap-2">
                  {card.thumb_urls.map((url, i) => (
                    <img
                      key={url}
                      src={url}
                      alt={t("preview.albumAlt", { n: i + 1 })}
                      className="h-16 w-16 rounded object-cover"
                    />
                  ))}
                </div>
              ) : null}
              {card.has_text && card.text ? (
                <div
                  className={
                    card.kind === "rich_message"
                      ? "telegram-rich-preview text-sm"
                      : "telegram-preview-text text-sm"
                  }
                  dangerouslySetInnerHTML={{ __html: card.text }}
                />
              ) : card.kind === "photo" && !card.cover_url ? (
                <p className="text-xs text-text-muted">{t("preview.coverMissing")}</p>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
