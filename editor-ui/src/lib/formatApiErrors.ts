import { t } from "@/i18n";

const FIELD_KEYS = {
  body: "field.body",
  title: "field.title",
  slug: "field.slug",
  status: "field.status",
  short_description: "field.shortDescription",
} as const;

export function formatApiErrors(payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return t("postEdit.saveFailed");
  }
  const record = payload as {
    errors?: Record<string, string[] | string>;
    error?: string;
    detail?: string;
  };
  if (record.errors) {
    return Object.entries(record.errors)
      .flatMap(([field, msgs]) => {
        const list = Array.isArray(msgs) ? msgs : [String(msgs)];
        const key = FIELD_KEYS[field as keyof typeof FIELD_KEYS];
        const label = key ? t(key) : field;
        return list.map((message) => `${label}: ${message}`);
      })
      .join(" · ");
  }
  return record.error || record.detail || t("postEdit.saveFailed");
}
