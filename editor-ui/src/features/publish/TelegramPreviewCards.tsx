import type { TelegramPreviewCard, TelegramPreviewPayload } from "@/api/types";

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
  return (
    <div className="space-y-4">
      {layoutSource && (
        <p className="text-xs text-text-muted">
          {layoutSource}
          {ownerPremium !== null && ownerPremium !== undefined && (
            <>
              {" "}
              Owner Premium: <strong>{ownerPremium ? "yes" : "no"}</strong>.
            </>
          )}
        </p>
      )}
      {previewPayload && (
        <p className="text-xs text-text-muted">
          {previewPayload.is_series
            ? `Series: ${previewPayload.step_count} text parts, `
            : "Single post, "}
          {previewPayload.send_count} Telegram sends total.
          {previewPayload.has_subscription
            ? " Premium channel (album caption on first photo; cover-only may split text)."
            : telegramFormat === "crosslink"
              ? " Crosslink: single text message with linked label and tags."
              : " Standard layout (caption on cover or album when text fits)."}
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
                Send {card.send_index}/{card.send_total}
              </span>
              <strong className="text-sm text-text-primary">{card.title}</strong>
              <span className="text-text-muted">
                Step {card.step_index}/{card.step_total} — {card.step_label}
                {card.step_is_continuation ? " (продолжение)" : ""}
              </span>
              {card.max_chars ? (
                <span
                  className={
                    card.char_count > card.max_chars
                      ? "font-medium text-red-600"
                      : "text-text-muted"
                  }
                >
                  {card.char_count} / {card.max_chars} chars
                </span>
              ) : card.kind === "media_group" ? (
                <span className="text-text-muted">
                  {card.image_count} photo{card.image_count === 1 ? "" : "s"}
                </span>
              ) : null}
            </header>
            <div className="space-y-3 p-3">
              {card.limit_note && (
                <p className="text-xs text-amber-700">{card.limit_note}</p>
              )}
              {card.cover_url && (
                <img
                  src={card.cover_url}
                  alt="Cover"
                  className="max-h-48 rounded-lg object-cover"
                />
              )}
              {card.thumb_row && card.thumb_urls?.length ? (
                <div className="flex flex-wrap gap-2">
                  {card.thumb_urls.map((url, i) => (
                    <img
                      key={url}
                      src={url}
                      alt={`Album ${i + 1}`}
                      className="h-16 w-16 rounded object-cover"
                    />
                  ))}
                </div>
              ) : null}
              {card.has_text && card.text ? (
                <div
                  className="prose prose-sm max-w-none text-sm"
                  dangerouslySetInnerHTML={{ __html: card.text }}
                />
              ) : card.kind === "photo" && !card.cover_url ? (
                <p className="text-xs text-text-muted">Cover file not found on disk.</p>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
