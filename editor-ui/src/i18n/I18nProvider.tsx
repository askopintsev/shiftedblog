import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  localeToBcp47,
  readStoredLocale,
  type Locale,
} from "./locales";
import {
  setActiveLocale,
  t as translate,
  type MessageKey,
  type TranslateParams,
} from "./t";

type TranslateFn = (key: MessageKey, params?: TranslateParams) => string;

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: TranslateFn;
  bcp47: string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function applyDocumentLang(locale: Locale): void {
  document.documentElement.lang = locale;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const initial = readStoredLocale();
    setActiveLocale(initial);
    return initial;
  });

  useEffect(() => {
    setActiveLocale(locale);
    applyDocumentLang(locale);
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setActiveLocale(next);
    setLocaleState(next);
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const t = useCallback<TranslateFn>(
    (key, params) => {
      void locale;
      return translate(key, params);
    },
    [locale],
  );

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale,
      t,
      bcp47: localeToBcp47(locale),
    }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}

export function useT(): TranslateFn {
  return useI18n().t;
}

export function getDefaultLocale(): Locale {
  return DEFAULT_LOCALE;
}
