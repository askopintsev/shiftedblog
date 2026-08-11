export const LOCALES = ["ru", "en"] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "ru";

export const LOCALE_STORAGE_KEY = "shiftedblog-editor-locale";

export function isLocale(value: unknown): value is Locale {
  return value === "ru" || value === "en";
}

export function localeToBcp47(locale: Locale): string {
  return locale === "en" ? "en-US" : "ru-RU";
}

export function readStoredLocale(): Locale {
  try {
    const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (isLocale(stored)) return stored;
  } catch {
    /* ignore */
  }
  return DEFAULT_LOCALE;
}
