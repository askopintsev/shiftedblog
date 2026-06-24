const FIELD_LABELS: Record<string, string> = {
  body: "Текст",
  title: "Заголовок",
  slug: "Slug",
  status: "Статус",
  short_description: "Краткое описание",
};

export function formatApiErrors(payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return "Не удалось сохранить.";
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
        const label = FIELD_LABELS[field] ?? field;
        return list.map((message) => `${label}: ${message}`);
      })
      .join(" · ");
  }
  return record.error || record.detail || "Не удалось сохранить.";
}
