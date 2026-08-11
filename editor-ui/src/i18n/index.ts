export {
  DEFAULT_LOCALE,
  LOCALES,
  LOCALE_STORAGE_KEY,
  isLocale,
  localeToBcp47,
  readStoredLocale,
  type Locale,
} from "./locales";
export { I18nProvider, useI18n, useT } from "./I18nProvider";
export { t, getLocale, setActiveLocale, type MessageKey, type TranslateParams } from "./t";
