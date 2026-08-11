export function parseTagsInput(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export function formatTagsInput(tags: string[]): string {
  return tags.join(", ");
}

/** Text after the last comma (the token currently being typed). */
export function activeTagFragment(value: string): string {
  const parts = value.split(",");
  return (parts[parts.length - 1] ?? "").trimStart();
}

/** Replace the active fragment with ``tag``, keeping completed tags. */
export function applyTagSuggestion(value: string, tag: string): string {
  const lastComma = value.lastIndexOf(",");
  const selected = parseTagsInput(
    lastComma === -1 ? "" : value.slice(0, lastComma + 1),
  );
  const already = selected.some(
    (item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase(),
  );
  if (already) {
    return formatTagsInput(selected);
  }
  if (lastComma === -1) {
    return `${tag}, `;
  }
  const prefix = `${value.slice(0, lastComma + 1).replace(/\s*$/, "")} `;
  return `${prefix}${tag}, `;
}

export function filterTagSuggestions(
  allTags: string[],
  value: string,
  limit = 8,
): string[] {
  const fragment = activeTagFragment(value).toLocaleLowerCase();
  if (!fragment) {
    return [];
  }
  const selected = new Set(
    parseTagsInput(value).map((tag) => tag.toLocaleLowerCase()),
  );
  return allTags
    .filter((tag) => {
      const lower = tag.toLocaleLowerCase();
      return lower.includes(fragment) && !selected.has(lower);
    })
    .slice(0, limit);
}
