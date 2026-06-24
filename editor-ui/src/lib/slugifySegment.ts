/**
 * Mirrors editor.models.post.slugify_segment for admin prepopulated_fields parity.
 */

const CYRILLIC_TO_LATIN: readonly (readonly [string, string])[] = [
  ["щ", "shch"],
  ["ш", "sh"],
  ["ч", "ch"],
  ["ц", "ts"],
  ["ю", "yu"],
  ["я", "ya"],
  ["ё", "yo"],
  ["ж", "zh"],
  ["х", "kh"],
  ["э", "e"],
  ["ы", "y"],
  ["ъ", ""],
  ["ь", ""],
  ["а", "a"],
  ["б", "b"],
  ["в", "v"],
  ["г", "g"],
  ["д", "d"],
  ["е", "e"],
  ["з", "z"],
  ["и", "i"],
  ["й", "y"],
  ["к", "k"],
  ["л", "l"],
  ["м", "m"],
  ["н", "n"],
  ["о", "o"],
  ["п", "p"],
  ["р", "r"],
  ["с", "s"],
  ["т", "t"],
  ["у", "u"],
  ["ф", "f"],
];

function transliterateCyrillicToLatin(text: string): string {
  if (!text) return "";
  const lower = text.toLowerCase();
  const parts: string[] = [];
  let i = 0;
  while (i < lower.length) {
    let matched = false;
    for (const [cyr, lat] of CYRILLIC_TO_LATIN) {
      if (lower.startsWith(cyr, i)) {
        parts.push(lat);
        i += cyr.length;
        matched = true;
        break;
      }
    }
    if (!matched) {
      parts.push(text[i] ?? "");
      i += 1;
    }
  }
  return parts.join("");
}

export function slugifySegment(value: string): string {
  const cleaned = transliterateCyrillicToLatin((value || "").trim());
  return cleaned
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/[-\s]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
