import type { Locale } from "./locales";
import { DEFAULT_LOCALE } from "./locales";
import { en } from "./messages/en";
import { ru, type MessageKey } from "./messages/ru";

export type { MessageKey };
export type TranslateParams = Record<string, string | number>;

const catalogs: Record<Locale, Record<MessageKey, string>> = {
  ru,
  en,
};

let activeLocale: Locale = DEFAULT_LOCALE;

export function getLocale(): Locale {
  return activeLocale;
}

export function setActiveLocale(locale: Locale): void {
  activeLocale = locale;
}

function interpolate(template: string, params?: TranslateParams): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, key: string) => {
    const value = params[key];
    return value === undefined ? match : String(value);
  });
}

export function t(key: MessageKey, params?: TranslateParams): string {
  const catalog = catalogs[activeLocale] ?? catalogs[DEFAULT_LOCALE];
  const template = catalog[key] ?? catalogs[DEFAULT_LOCALE][key] ?? key;
  return interpolate(template, params);
}
