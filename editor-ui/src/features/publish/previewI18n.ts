import type { TelegramPreviewCard } from "@/api/types";
import { t, type MessageKey } from "@/i18n";

const LAYOUT_SOURCE_KEYS: Record<string, MessageKey> = {
  "Owner has no Premium: cover caption + gallery when possible.":
    "preview.layout.noPremium",
  "Owner has Premium but layout override is off.":
    "preview.layout.ownerPremiumOverrideOff",
  "Standard layout (caption + gallery when one post fits).":
    "preview.layout.standard",
  "Channel owner has Telegram Premium; album uses caption on first photo.":
    "preview.layout.channelOwnerPremium",
  "Cover-only posts may send text separately; album uses caption on first photo.":
    "preview.layout.coverOnlyMaySplit",
  "Premium layout from credentials or env (album caption on first photo).":
    "preview.layout.premiumFromCreds",
};

const TITLE_KEYS: Record<string, MessageKey> = {
  sendRichMessage: "preview.title.sendRichMessage",
  sendMessage: "preview.title.sendMessage",
  "sendPhoto (cover)": "preview.title.sendPhotoCover",
  sendMediaGroup: "preview.title.sendMediaGroup",
};

const STEP_LABEL_KEYS: Record<string, MessageKey> = {
  Продолжение: "preview.stepLabel.continuation",
  "Первый пост (альбом)": "preview.stepLabel.firstAlbum",
  "Первый пост (обложка)": "preview.stepLabel.firstCover",
  Пост: "preview.stepLabel.post",
  Continuation: "preview.stepLabel.continuation",
  "First post (album)": "preview.stepLabel.firstAlbum",
  "First post (cover)": "preview.stepLabel.firstCover",
  Post: "preview.stepLabel.post",
};

export function translateLayoutSource(source: string | null | undefined): string {
  if (!source) return "";
  const key = LAYOUT_SOURCE_KEYS[source];
  return key ? t(key) : source;
}

export function translateCardTitle(title: string): string {
  const key = TITLE_KEYS[title];
  return key ? t(key) : title;
}

export function translateStepLabel(label: string): string {
  const key = STEP_LABEL_KEYS[label];
  return key ? t(key) : label;
}

export function translateLimitNote(
  note: string | null | undefined,
  card: TelegramPreviewCard,
): string {
  if (!note) return "";

  let match = note.match(
    /^Rich message with (\d+) inline image\(s\); limit (\d+) UTF-8 characters \(HTML tags count\)\.$/,
  );
  if (match) {
    return t("preview.note.richWithImages", {
      n: match[1],
      m: match[2],
    });
  }

  match = note.match(
    /^Rich message limit (\d+) UTF-8 characters \(HTML tags count\)\.$/,
  );
  if (match) {
    return t("preview.note.richLimit", { m: match[1] });
  }

  match = note.match(/^Message limit (\d+) characters\.$/);
  if (match) {
    return t("preview.note.messageLimit", { m: match[1] });
  }

  if (
    note ===
    "Premium layout: cover is sent without caption; text follows as a separate message."
  ) {
    return t("preview.note.premiumCoverNoCaption");
  }

  match = note.match(
    /^Caption ends at the last complete sentence \(max (\d+) characters\); remainder in the next message\.$/,
  );
  if (match) {
    return t("preview.note.captionSplit", { m: match[1] });
  }

  match = note.match(/^Text fits in photo caption \(max (\d+) characters\)\.$/);
  if (match) {
    return t("preview.note.captionFits", { m: match[1] });
  }

  if (note === "Cover photo without caption.") {
    return t("preview.note.coverNoCaption");
  }

  match = note.match(
    /^Caption on the first album photo \(max (\d+) characters\)\.$/,
  );
  if (match) {
    return t("preview.note.albumCaption", { m: match[1] });
  }

  if (note === "Album without caption.") {
    return t("preview.note.albumNoCaption");
  }

  match = note.match(
    /^Album (\d+)\/(\d+) — up to (\d+) photos per send\.$/,
  );
  if (match) {
    return t("preview.note.albumChunk", {
      i: match[1],
      total: match[2],
      m: match[3],
    });
  }

  // Fall back using card fields for rich notes if API wording drifts.
  if (card.kind === "rich_message" && card.max_chars) {
    if ((card.image_count ?? 0) > 0) {
      return t("preview.note.richWithImages", {
        n: card.image_count ?? 0,
        m: card.max_chars,
      });
    }
    return t("preview.note.richLimit", { m: card.max_chars });
  }

  return note;
}
