import { LOCALES, useI18n } from "@/i18n";
import { cn } from "@/lib/utils";

export function InterfacePage() {
  const { locale, setLocale, t } = useI18n();

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold">{t("interface.title")}</h1>
      <div className="max-w-xl space-y-4 rounded-lg border border-border bg-surface p-4">
        <div>
          <div className="text-sm font-medium">{t("interface.language")}</div>
          <p className="mt-1 text-xs text-text-muted">
            {t("interface.languageHelp")}
          </p>
        </div>
        <div className="flex gap-2">
          {LOCALES.map((code) => (
            <button
              key={code}
              type="button"
              onClick={() => setLocale(code)}
              className={cn(
                "rounded-lg px-4 py-2 text-sm",
                locale === code
                  ? "bg-accent text-white"
                  : "border border-border bg-surface-muted text-text-secondary hover:bg-surface",
              )}
            >
              {code === "ru" ? t("interface.localeRu") : t("interface.localeEn")}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
